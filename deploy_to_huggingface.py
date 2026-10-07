#!/usr/bin/env python3
"""
Assistant de Déploiement Automatique vers Hugging Face Spaces
Permet de créer et mettre en ligne le Space Docker (16 Go RAM gratuits à vie)
en un clic, avec suivi en temps réel.
Auteur : Agent IA Commercial
"""

import os
import sys
import json
import base64
import getpass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

IGNORE_PATTERNS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".cache",
    "cloudflared",
    "cloudflared-linux-amd64",
    ".env.local",
    "venv",
    ".venv"
}

def is_ignored(path: Path) -> bool:
    for part in path.parts:
        if part in IGNORE_PATTERNS or part.endswith(".pyc") or part.endswith(".swp"):
            return True
    return False

def deploy():
    print("""
========================================================================
   🚀 DÉPLOIEMENT CLOUD : HUGGING FACE SPACES (Docker 16 Go RAM)
========================================================================
   Ce script configure et déploie votre plateforme commerciale autonome
   sur Hugging Face Spaces. Votre agent fonctionnera 24h/24 sans nécessiter
   que votre PC personnel reste allumé.
========================================================================
    """)

    import argparse
    parser = argparse.ArgumentParser(description="Déployer sur Hugging Face Spaces")
    parser.add_argument("--token", "-t", help="Token d'accès Hugging Face (Write)", default=None)
    parser.add_argument("--space", "-s", help="Nom du Space", default=None)
    parser.add_argument("--private", action="store_true", help="Rendre le Space privé")
    args, _ = parser.parse_known_args()

    hf_token = args.token or os.environ.get("HF_TOKEN", "").strip()
    if not hf_token:
        print("Pour déployer, vous avez besoin de votre Token Hugging Face (rôle: Write).")
        print("Si vous n'en avez pas : connectez-vous sur https://huggingface.co/settings/tokens")
        print("et créez un token avec les permissions 'Write'.\n")
        try:
            hf_token = input("👉 Entrez votre Hugging Face Token (hf_...) : ").strip()
        except EOFError:
            print("Erreur: Token non renseigné.")
            return

    if not hf_token:
        print("❌ Token manquant. Déploiement annulé.")
        return

    # Vérification du token avec l'API Hugging Face
    import urllib.request
    import urllib.error

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "User-Agent": "HF-Deployer/1.0"
    }

    print("\n🔍 Vérification des identifiants Hugging Face...")
    req = urllib.request.Request("https://huggingface.co/api/whoami-v2", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            user_data = json.loads(resp.read().decode("utf-8"))
            username = user_data.get("name")
            print(f"✅ Connecté avec succès en tant que : {username}")
    except urllib.error.HTTPError as e:
        print(f"❌ Erreur d'authentification ({e.code}) : Token Hugging Face invalide ou expiré.")
        return
    except Exception as e:
        print(f"❌ Erreur réseau lors de la vérification : {e}")
        return

    default_space_name = "commercial-ia-autonome"
    if args.space:
        space_name = args.space.strip()
    else:
        try:
            custom_name = input(f"\n👉 Nom du Space [{default_space_name}] : ").strip()
        except EOFError:
            custom_name = ""
        space_name = custom_name if custom_name else default_space_name

    is_private = bool(args.private)

    repo_id = f"{username}/{space_name}"
    print(f"\n📦 Préparation du Space : {repo_id} (SDK: Docker, Privé: {is_private})...")

    # 1. Création du Space via l'API Hugging Face
    create_url = "https://huggingface.co/api/repos/create"
    create_payload = json.dumps({
        "type": "space",
        "name": space_name,
        "sdk": "docker",
        "private": is_private
    }).encode("utf-8")
    
    create_req = urllib.request.Request(
        create_url,
        data=create_payload,
        headers={**headers, "Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(create_req, timeout=15) as resp:
            print(f"✅ Nouveau Space créé : https://huggingface.co/spaces/{repo_id}")
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print(f"ℹ️ Le Space {repo_id} existe déjà. Mise à jour des fichiers...")
        else:
            print(f"⚠️ Erreur lors de la création ({e.code}) : {e.read().decode('utf-8')}")

    # 2. Utilisation de huggingface_hub si disponible, sinon commit API
    try:
        from huggingface_hub import HfApi
        print("\n🚀 Téléversement des fichiers via le client officiel Hugging Face...")
        api = HfApi(token=hf_token)
        api.upload_folder(
            folder_path=str(BASE_DIR),
            repo_id=repo_id,
            repo_type="space",
            commit_message="Déploiement Plateforme Commerciale IA Autonome (Docker HF)",
            ignore_patterns=list(IGNORE_PATTERNS) + ["*.pyc"]
        )
        print("✅ Tous les fichiers ont été téléversés avec succès !")
    except ImportError:
        print("\n🚀 Téléversement des fichiers via l'API REST directe...")
        # Fallback upload via direct commit API
        # Lecture des fichiers
        operations = []
        for file_path in BASE_DIR.rglob("*"):
            if file_path.is_file() and not is_ignored(file_path.relative_to(BASE_DIR)):
                rel_path = file_path.relative_to(BASE_DIR).as_posix()
                try:
                    with open(file_path, "rb") as f:
                        content_bytes = f.read()
                        b64_content = base64.b64encode(content_bytes).decode("ascii")
                        operations.append({
                            "key": "file",
                            "value": {
                                "path": rel_path,
                                "encoding": "base64",
                                "content": b64_content
                            }
                        })
                except Exception as err:
                    print(f"Fichier ignoré ({err}) : {rel_path}")

        print(f"📁 {len(operations)} fichiers préparés pour le déploiement.")
        
        # Envoi via commit REST endpoint
        commit_url = f"https://huggingface.co/api/spaces/{repo_id}/commit/main"
        commit_payload = json.dumps({
            "operations": operations,
            "commit_message": "Déploiement Plateforme Commerciale IA Autonome (Docker HF)"
        }).encode("utf-8")

        commit_req = urllib.request.Request(
            commit_url,
            data=commit_payload,
            headers={**headers, "Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(commit_req, timeout=120) as resp:
                print("✅ Fichiers synchronisés sur Hugging Face Spaces !")
        except Exception as e:
            print(f"❌ Erreur lors du commit REST : {e}")
            return

    direct_url = f"https://{username.lower()}-{space_name.lower().replace('_', '-')}.hf.space"
    space_page = f"https://huggingface.co/spaces/{repo_id}"

    print(f"""
========================================================================
   🎉 DÉPLOIEMENT INITIÉ AVEC SUCCÈS !
========================================================================
   Votre conteneur Docker est en cours de compilation automatique
   sur les serveurs Hugging Face (16 Go de RAM alloués).

   👉 Page de suivi du Space :
      {space_page}

   👉 Lien d'accès direct de votre Application (une fois compilée) :
      {direct_url}

   🔑 Rappel Sécurité :
      - Console Directeur protégée par le Pass Maître : Sagbo2026!
      - Pages de vente publiques : {direct_url}/vente/1
========================================================================
    """)

if __name__ == "__main__":
    deploy()
