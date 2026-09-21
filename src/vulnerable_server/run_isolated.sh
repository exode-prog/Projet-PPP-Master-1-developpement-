#!/bin/bash
# Script de lancement contrôlé du serveur MCP vulnérable (Sprint 3).
# Affiche un avertissement explicite et demande confirmation avant de démarrer.

set -e

echo "=========================================================="
echo "⚠️   ATTENTION — SERVEUR MCP VOLONTAIREMENT VULNÉRABLE   ⚠️"
echo "=========================================================="
echo ""
echo "Ce serveur contient une injection de commande (CWE-78)"
echo "introduite délibérément à des fins pédagogiques (Sprint 3)."
echo ""
echo "Il ne doit JAMAIS être exposé en dehors de cet environnement"
echo "de laboratoire isolé."
echo ""
echo "Voir docs/vulnerabilite-sprint3.md pour le détail complet."
echo ""
read -p "Confirmez-vous vouloir lancer ce serveur en environnement isolé ? (oui/non) : " confirmation

if [ "$confirmation" != "oui" ]; then
    echo "Lancement annulé."
    exit 1
fi

echo ""
echo "Lancement du serveur vulnérable (transport stdio par défaut)..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/server.py"
