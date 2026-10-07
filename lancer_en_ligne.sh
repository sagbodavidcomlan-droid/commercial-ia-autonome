#!/usr/bin/env bash
# ==============================================================================
# Invo. — Lancement en Ligne Mondial Gratuit & URL Personnalisable
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

# Exporter le PATH Node.js si présent dans nvm pour npx / localtunnel
if [ -d "/home/dave/.nvm/versions/node/v22.14.0/bin" ]; then
    export PATH="/home/dave/.nvm/versions/node/v22.14.0/bin:$PATH"
fi

CUSTOM_NAME="${1:-}"

echo "========================================================================"
echo "   🚀 INVO. — MISE EN LIGNE GRATUITE & ACCÈS MONDIAL"
echo "========================================================================"
echo ""

# 1. Vérifier si le serveur local est déjà en marche sur le port 8000
if ! curl -s http://127.0.0.1:8000/api/dashboard > /dev/null 2>&1; then
    echo "▶ Démarrage du serveur Invo sur le port 8000..."
    python3 app.py 8000 > server.log 2>&1 &
    SERVER_PID=$!
    sleep 3
    echo "✅ Serveur local actif (PID: $SERVER_PID)"
else
    echo "✅ Serveur local déjà actif sur http://localhost:8000"
fi

# 2. Choix du mode : URL Personnalisée (Localtunnel) ou Cloudflare
USE_LOCALTUNNEL=0
if [ -n "$CUSTOM_NAME" ] && command -v npx >/dev/null 2>&1; then
    USE_LOCALTUNNEL=1
fi

if [ "$USE_LOCALTUNNEL" -eq 1 ]; then
    echo "▶ Activation de votre lien personnalisé : https://$CUSTOM_NAME.loca.lt"
    rm -f tunnel.log
    npx --yes localtunnel --port 8000 --subdomain "$CUSTOM_NAME" > tunnel.log 2>&1 &
    TUNNEL_PID=$!
    
    URL=""
    for i in {1..20}; do
        sleep 1
        if [ -f tunnel.log ]; then
            URL=$(grep -oE "https://[a-zA-Z0-9-]+\.loca\.lt" tunnel.log | head -n 1 || true)
            if [ -n "$URL" ]; then
                break
            fi
        fi
    done
fi

# Fallback sur Cloudflare Tunnel si pas de sous-domaine personnalisé ou si non dispo
if [ -z "$URL" ]; then
    if [ ! -f "./cloudflared" ]; then
        echo "▶ Téléchargement du binaire sécurisé Cloudflare Tunnel..."
        curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ./cloudflared
        chmod +x ./cloudflared
    fi

    echo "▶ Génération de l'accès public HTTPS mondial via Cloudflare..."
    rm -f tunnel.log
    ./cloudflared tunnel --url http://127.0.0.1:8000 > tunnel.log 2>&1 &
    TUNNEL_PID=$!

    for i in {1..30}; do
        sleep 1
        if [ -f tunnel.log ]; then
            URL=$(grep -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" tunnel.log | head -n 1 || true)
            if [ -n "$URL" ]; then
                break
            fi
        fi
    done
fi

if [ -z "$URL" ]; then
    echo "⚠️ Le tunnel met un peu de temps. Consultez le log avec : cat tunnel.log"
    exit 1
fi

echo ""
echo "========================================================================"
echo "   🎉 VOTRE APPLICATION EST EN LIGNE ET ACCESSIBLE PARTOUT DANS LE MONDE !"
echo "========================================================================"
echo ""
echo "   👉 URL PUBLIQUE DU TABLEAU DE BORD (Tous navigateurs & mobiles) :"
echo "      $URL"
echo ""
echo "   🛍️ EXEMPLES DE PAGES DE VENTE CLÉ EN MAIN (Haute Conversion) :"
echo "      $URL/vente/1"
echo "      $URL/vente/6"
echo ""
echo "   📱 INSTALLATION DE L'APPLICATION MOBILE (PWA) :"
echo "      1. Ouvrez $URL sur votre téléphone (Safari sur iPhone ou Chrome sur Android)"
echo "      2. Cliquez sur 'Partager' (iPhone) ou les 3 points (Android)"
echo "      3. Choisissez 'Ajouter à l'écran d'accueil'"
echo "      -> Vous avez maintenant une vraie application mobile sans passer par l'App Store !"
echo ""
echo "   💡 ASTUCE : POUR CHOISIR UN LIEN 100% PERSONNALISÉ :"
echo "      Relancez simplement avec : ./lancer_en_ligne.sh mon-agence"
echo "      Vous obtiendrez alors : https://mon-agence.loca.lt"
echo "========================================================================"
echo "Tunnel actif (PID: $TUNNEL_PID). Appuyez sur Ctrl+C pour arrêter."

wait $TUNNEL_PID
