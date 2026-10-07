#!/usr/bin/env bash
# =====================================================================
# Lanceur 1-Clic de la Console Commerciale IA & Direction Générale
# =====================================================================

PORT=${1:-8000}

echo "========================================================================"
echo "   🚀 DÉMARRAGE DE LA CONSOLE COMMERCIALE IA (UNITÉ AUTONOME)"
echo "   Direction Commerciale & Supervision des Ventes"
echo "========================================================================"
echo ""
echo "👉 Accédez à la console logicielle dans votre navigateur :"
echo ""
echo "       🌐 http://localhost:$PORT"
echo "       (ou http://127.0.0.1:$PORT)"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter le serveur à tout moment."
echo "========================================================================"
echo ""

# Nettoyage automatique préventif pour s'assurer que le port est disponible
fuser -k ${PORT}/tcp 2>/dev/null || true
sleep 0.5

# Démarrage du serveur applicatif avec Python natif (0 dépendance externe requise)
python3 app.py $PORT
