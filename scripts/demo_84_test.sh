#!/bin/bash
# Lance une requete Ollama -> MCP et affiche le journal d'audit apres coup.
# Prechauffe le modele a chaque execution (au cas ou Ollama l'ait deja
# decharge de la memoire), pour eviter un token expire pendant le chargement.
set -e
cd "$(dirname "$0")/.."
echo "--- Prechauffage du modele (securite anti-expiration du token) ---"
ollama run qwen2.5:3b "dis juste OK" > /dev/null
echo "--- Generation d'un token frais ---"
TOKEN=$(./scripts/keycloak_get_token.sh)
python3 scripts/ollama_mcp_bridge.py "http://localhost:9000/mcp" "$TOKEN" "utilise l'outil hello avec le nom Exode" qwen2.5:3b
echo ""
echo "--- Journal d'audit (5 dernieres entrees) ---"
docker exec mcp-target-server-1 tail -5 audit.log
