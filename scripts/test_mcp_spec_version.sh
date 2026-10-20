#!/bin/bash
# Verifie la version de la spec MCP reellement negociee par la gateway
# (point jury 1 : "indiquer la version de la spec MCP reellement utilisee").
set -e
cd "$(dirname "$0")/.."

echo "--- Version la plus recente connue du SDK mcp installe ---"
python3 -c "from mcp.types import LATEST_PROTOCOL_VERSION, DEFAULT_NEGOTIATED_VERSION; print('LATEST_PROTOCOL_VERSION =', LATEST_PROTOCOL_VERSION); print('DEFAULT_NEGOTIATED_VERSION =', DEFAULT_NEGOTIATED_VERSION)"

test_version() {
  local requested="$1"
  local label="$2"
  local token
  token=$(./scripts/keycloak_get_token.sh)
  echo ""
  echo "--- Client demande protocolVersion=$requested ($label) ---"
  curl -s -X POST http://127.0.0.1:9000/mcp -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"$requested\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"}}}" \
    | grep -o '"protocolVersion":"[^"]*"'
}

test_version "2024-11-05" "ancienne version"
test_version "2025-11-25" "version la plus recente connue du SDK"
test_version "1999-01-01" "version invalide, teste le comportement de repli"
