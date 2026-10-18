#!/usr/bin/env python3
"""
Superviseur autonome de la passerelle WhatsApp (Baileys Node.js)
Lance et maintient automatiquement en vie le pont WhatsApp local (port 3001)
pour permettre l'affichage du QR Code et l'appairage direct.
"""

import os
import sys
import time
import shutil
import logging
import threading
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path

logger = logging.getLogger("WhatsAppBridgeDaemon")

BASE_DIR = Path(__file__).resolve().parent.parent
BRIDGE_DIR = BASE_DIR / "whatsapp_bridge"
SERVER_JS = BRIDGE_DIR / "server.js"

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
        self.bridge_url = f"http://localhost:{self.port}"

    def is_bridge_reachable(self) -> bool:
        """Vérifie si la passerelle répond déjà sur HTTP /status."""
        try:
            req = urllib.request.Request(f"{self.bridge_url}/status", headers={"User-Agent": "BridgeSupervisor/1.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def start(self):
        """Démarre le thread de supervision de la passerelle WhatsApp."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._supervise_loop, daemon=True, name="WhatsAppBridgeSupervisor")
        self.thread.start()
        logger.info("Superviseur de la passerelle WhatsApp démarré.")

    def _supervise_loop(self):
        node_bin = shutil.which("node")
        if not node_bin:
            logger.warning("Node.js introuvable sur le système. La passerelle QR Code ne peut pas être démarrée automatiquement.")
            return

        if not SERVER_JS.exists():
            logger.warning(f"Fichier {SERVER_JS} introuvable.")
            return

        logger.info(f"Node.js détecté : {node_bin}. Surveillance de la passerelle WhatsApp sur le port {self.port}...")

        while self.running:
            if not self.is_bridge_reachable():
                logger.info("La passerelle WhatsApp (port 3001) n'est pas active. Lancement du processus Node.js...")
                try:
                    self.process = subprocess.Popen(
                        [node_bin, "server.js"],
                        cwd=str(BRIDGE_DIR),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )
                    logger.info(f"Processus WhatsApp Bridge démarré (PID: {self.process.pid})")

                    for _ in range(15):
                        time.sleep(1)
                        if self.is_bridge_reachable():
                            logger.info("Passerelle WhatsApp opérationnelle sur http://localhost:3001")
                            break
                        if self.process.poll() is not None:
                            logger.warning(f"Le processus WhatsApp Bridge s'est arrêté (Code: {self.process.returncode})")
                            break

                except Exception as e:
                    logger.error(f"Erreur lors du lancement de la passerelle WhatsApp Node.js: {e}")

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
