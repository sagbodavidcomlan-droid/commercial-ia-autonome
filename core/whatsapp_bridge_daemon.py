#!/usr/bin/env python3
"""
Superviseur autonome de la passerelle WhatsApp (Baileys Node.js)
Lance et maintient automatiquement en vie le pont WhatsApp local (port 3001)
pour permettre l'affichage du QR Code et l'appairage direct.
Capacité d'auto-installation de Node.js portable en environnement cloud sans privilèges root.
"""

import os
import sys
import time
import shutil
import tarfile
import logging
import platform
import threading
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("WhatsAppBridgeDaemon")

BASE_DIR = Path(__file__).resolve().parent.parent
BRIDGE_DIR = BASE_DIR / "whatsapp_bridge"
SERVER_JS = BRIDGE_DIR / "server.js"
PORTABLE_NODE_DIR = BRIDGE_DIR / ".node"

NODE_TARBALL_URL = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-linux-x64.tar.xz"

class WhatsAppBridgeDaemon:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(WhatsAppBridgeDaemon, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.process = None
        self.running = False
        self.thread = None
        self.port = int(os.getenv("WHATSAPP_BRIDGE_PORT", "3001"))
        self.bridge_url = f"http://127.0.0.1:{self.port}"
        self.cached_node_path = None
        self.status_message = "Initialisation..."

    def find_node_binary(self) -> Optional[str]:
        """Détecte Node.js sur le système ou installe Node.js portable si absent."""
        if self.cached_node_path and os.path.exists(self.cached_node_path):
            return self.cached_node_path

        # 1. Vérifier dans le PATH standard
        for cmd in ("node", "nodejs"):
            found = shutil.which(cmd)
            if found:
                self.cached_node_path = found
                return found

        # 2. Vérifier les répertoires d'installation usuels
        candidates = [
            "/usr/bin/node",
            "/usr/local/bin/node",
            str(PORTABLE_NODE_DIR / "bin" / "node"),
            os.path.expanduser("~/.nvm/versions/node/v20.18.0/bin/node"),
            os.path.expanduser("~/.nvm/versions/node/v22.14.0/bin/node"),
        ]
        for p in candidates:
            if os.path.exists(p) and os.access(p, os.X_OK):
                self.cached_node_path = p
                return p

        # 3. Si Linux x86_64, tenter le téléchargement de Node portable sans privilège root
        if platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64"):
            try:
                portable_node = PORTABLE_NODE_DIR / "bin" / "node"
                if portable_node.exists() and os.access(str(portable_node), os.X_OK):
                    self.cached_node_path = str(portable_node)
                    return self.cached_node_path

                logger.info(f"Node.js absent. Téléchargement automatique de Node.js portable vers {PORTABLE_NODE_DIR}...")
                self.status_message = "Installation de Node.js portable en cours..."
                PORTABLE_NODE_DIR.mkdir(parents=True, exist_ok=True)
                tar_path = BRIDGE_DIR / "node_portable.tar.xz"

                req = urllib.request.Request(NODE_TARBALL_URL, headers={"User-Agent": "Sales-Agent-Installer/1.0"})
                with urllib.request.urlopen(req, timeout=40) as resp, open(tar_path, "wb") as out_f:
                    shutil.copyfileobj(resp, out_f)

                # Extraction
                with tarfile.open(tar_path, "r:xz") as tar:
                    for member in tar.getmembers():
                        # strip top-level directory (e.g. node-v20.18.0-linux-x64/bin/node -> bin/node)
                        parts = Path(member.name).parts
                        if len(parts) > 1:
                            member.name = str(Path(*parts[1:]))
                            tar.extract(member, path=str(PORTABLE_NODE_DIR))

                if tar_path.exists():
                    tar_path.unlink()

                if portable_node.exists():
                    os.chmod(str(portable_node), 0o755)
                    self.cached_node_path = str(portable_node)
                    logger.info("Node.js portable installé avec succès !")
                    return self.cached_node_path
            except Exception as e:
                logger.warning(f"Échec auto-installation Node portable: {e}")

        return None

    def is_bridge_reachable(self) -> bool:
        """Vérifie si la passerelle répond déjà sur HTTP /status."""
        try:
            req = urllib.request.Request(f"{self.bridge_url}/status", headers={"User-Agent": "BridgeSupervisor/1.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        node_bin = self.find_node_binary()
        is_up = self.is_bridge_reachable()
        return {
            "node_available": bool(node_bin),
            "node_path": node_bin or "Non détecté",
            "bridge_running": is_up,
            "bridge_url": self.bridge_url,
            "status_message": self.status_message,
            "pid": self.process.pid if (self.process and self.process.poll() is None) else None
        }

    def start(self):
        """Démarre le thread de supervision de la passerelle WhatsApp."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._supervise_loop, daemon=True, name="WhatsAppBridgeSupervisor")
        self.thread.start()
        logger.info("Superviseur de la passerelle WhatsApp démarré.")

    def _supervise_loop(self):
        node_bin = self.find_node_binary()
        if not node_bin:
            self.status_message = "Node.js introuvable sur le système hôte."
            logger.warning("Node.js introuvable sur le système. La passerelle QR Code ne peut pas être démarrée automatiquement.")
            return

        if not SERVER_JS.exists():
            self.status_message = f"Fichier {SERVER_JS} introuvable."
            logger.warning(f"Fichier {SERVER_JS} introuvable.")
            return

        # Préparation de l'environnement avec Node.js dans le PATH
        env = os.environ.copy()
        node_dir = str(Path(node_bin).parent)
        env["PATH"] = f"{node_dir}:{env.get('PATH', '')}"
        env["npm_config_cache"] = "/tmp/.npm-cache"
        env.pop("PORT", None)
        env["PORT"] = str(self.port)
        env["WHATSAPP_BRIDGE_PORT"] = str(self.port)

        # S'assurer que les modules node_modules sont installés
        baileys_dir = BRIDGE_DIR / "node_modules" / "@whiskeysockets" / "baileys"
        if not baileys_dir.exists():
            logger.info("Installation des dépendances npm pour whatsapp_bridge...")
            self.status_message = "Installation des dépendances WhatsApp (Baileys)..."
            npm_cli = PORTABLE_NODE_DIR / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js"
            if npm_cli.exists():
                npm_cmd = [node_bin, str(npm_cli), "install", "--production", "--no-audit", "--no-fund"]
            elif shutil.which("npm"):
                npm_cmd = [shutil.which("npm"), "install", "--production", "--no-audit", "--no-fund"]
            else:
                npm_cmd = [node_bin, str(Path(node_bin).parent / "npm"), "install", "--production", "--no-audit", "--no-fund"]

            try:
                logger.info(f"Exécution de : {' '.join(npm_cmd)}")
                res = subprocess.run(npm_cmd, cwd=str(BRIDGE_DIR), env=env, timeout=180, capture_output=True, text=True)
                if res.returncode == 0 and baileys_dir.exists():
                    logger.info("Dépendances Baileys installées avec succès.")
                    self.status_message = "Dépendances WhatsApp installées avec succès."
                else:
                    err_msg = res.stderr or res.stdout or f"code {res.returncode}"
                    logger.error(f"Échec npm install: {err_msg}")
                    self.status_message = f"Erreur npm: {err_msg.strip()[:140]}"
            except Exception as npm_err:
                logger.error(f"Erreur npm install: {npm_err}")
                self.status_message = f"Erreur npm install: {npm_err}"

        if not baileys_dir.exists():
            logger.warning("Baileys n'a pas pu être installé. En attente...")
            return

        logger.info(f"Node.js actif : {node_bin}. Surveillance de la passerelle WhatsApp sur le port {self.port}...")
        self.status_message = "Passerelle en cours d'exécution."

        while self.running:
            if not self.is_bridge_reachable():
                logger.info("La passerelle WhatsApp (port 3001) n'est pas active. Lancement du processus Node.js...")
                try:
                    log_file = BRIDGE_DIR / "bridge.log"
                    log_f = open(log_file, "a", encoding="utf-8")
                    self.process = subprocess.Popen(
                        [node_bin, "server.js"],
                        cwd=str(BRIDGE_DIR),
                        stdout=log_f,
                        stderr=subprocess.STDOUT,
                        env=env,
                        text=True
                    )
                    logger.info(f"Processus WhatsApp Bridge démarré (PID: {self.process.pid})")

                    for _ in range(15):
                        time.sleep(1)
                        if self.is_bridge_reachable():
                            logger.info("Passerelle WhatsApp opérationnelle sur http://127.0.0.1:3001")
                            self.status_message = "Passerelle WhatsApp active et joignable."
                            break
                        if self.process.poll() is not None:
                            err_out = ""
                            try:
                                if log_file.exists():
                                    with open(log_file, "r", encoding="utf-8") as f_err:
                                        err_out = f_err.read()[-1000:]
                            except Exception:
                                pass
                            logger.warning(f"Le processus WhatsApp Bridge s'est arrêté (Code: {self.process.returncode}): {err_out}")
                            self.status_message = f"Arrêt (code {self.process.returncode}): {err_out.strip()[:500]}"
                            break

                except Exception as e:
                    logger.error(f"Erreur lors du lancement de la passerelle WhatsApp Node.js: {e}")
                    self.status_message = f"Erreur démarrage: {e}"

            for _ in range(10):
                if not self.running:
                    break
                time.sleep(1)

    def stop(self):
        self.running = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        logger.info("Superviseur WhatsApp Bridge arrêté.")

whatsapp_bridge_daemon = WhatsAppBridgeDaemon()
