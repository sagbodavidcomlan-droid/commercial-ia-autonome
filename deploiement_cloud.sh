#!/usr/bin/env bash
# ==============================================================================
# Invo. — Déploiement Cloud Permanent Gratuit (24h/24 sans PC allumé)
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "========================================================================"
echo "   ☁️ INVO. — DÉPLOIEMENT CLOUD PERMANENT 100% GRATUIT (24H/24)"
echo "========================================================================"
echo ""
echo "Ce script configure votre hébergement cloud permanent pour que"
echo "votre commercial IA et vos pages de vente tournent 24h/24 en ligne,"
echo "même lorsque votre ordinateur est éteint."
echo ""

# 1. Vérifier si un dépôt Git local existe
if [ ! -d ".git" ]; then
    echo "▶ Initialisation du dépôt Git du projet..."
    # Utiliser python pour initialiser si git système n'est pas présent
    python3 -c "
import os, subprocess
if not os.path.exists('.git'):
    os.makedirs('.git', exist_ok=True)
" 2>/dev/null || true
fi

# 2. Créer l'archive propre prête pour le Cloud
echo "▶ Création de l'archive prête au déploiement (invo_cloud_bundle.zip)..."
python3 -c "
import zipfile, os

exclude_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.gemini'}
exclude_files = {'cloudflared', 'gh', 'server.log', 'tunnel.log', 'invo_cloud_bundle.zip'}

with zipfile.ZipFile('invo_cloud_bundle.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for f in files:
            if f not in exclude_files and not f.endswith('.pyc'):
                fp = os.path.join(root, f)
                arcname = os.path.relpath(fp, '.')
                zipf.write(fp, arcname)
print('✅ Archive invo_cloud_bundle.zip générée avec succès !')
"

echo ""
echo "========================================================================"
echo "   🌟 VOS 2 MÉTHODES LES PLUS SIMPLES POUR LE CLOUD PERMANENT :"
echo "========================================================================"
echo ""
echo "1. MÉTHODE RENDER.COM (Recommandée - 0€ / mois à vie) :"
echo "   a) Rendez-vous sur https://dashboard.render.com (Inscription gratuite en 30s avec Google/GitHub)"
echo "   b) Cliquez sur 'New +' -> 'Web Service'"
echo "   c) Connectez votre dépôt ou uploadez le code"
echo "   d) Render détecte automatiquement 'render.yaml' et déploie votre application !"
echo ""
echo "2. MÉTHODE HUGGING FACE SPACES (16 Go RAM Gratuits - 0€ / mois à vie) :"
echo "   a) Rendez-vous sur https://huggingface.co/new-space"
echo "   b) Nommez votre Space (ex: 'invo-commercial'), sélectionnez 'Docker' (Blank)"
echo "   c) Glissez-déposez les fichiers de 'invo_cloud_bundle.zip' ou connectez le repo"
echo "   d) Votre application tourne 24h/24 en ligne gratuitement sur son URL permanente !"
echo ""
echo "========================================================================"
