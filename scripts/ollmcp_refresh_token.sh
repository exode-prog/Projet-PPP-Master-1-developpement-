#!/bin/bash
# Nettoie l'ancien token stocke par ollmcp (dans sa config locale) et le remplace
# par un token Keycloak frais. Les tokens expirent vite (quelques minutes), donc
# ce script est a relancer juste avant chaque session ollmcp.
# Usage : ./ollmcp_refresh_token.sh [username] [password]
set -e
cd "$(dirname "$0")"

TOKEN=$(./keycloak_get_token.sh "$@")

echo "Nettoyage de l'ancien token stocke par ollmcp..."
ollmcp mcp remove mcp-secure-gateway 2>/dev/null || echo "(aucune config existante, on continue)"

echo "Enregistrement du nouveau token..."
ollmcp mcp add --transport http --header "Authorization: Bearer $TOKEN" mcp-secure-gateway http://localhost:9000/mcp

echo ""
echo "Token rafraichi avec succes. Lance maintenant :"
echo "  ollmcp --model qwen2.5:7b"
