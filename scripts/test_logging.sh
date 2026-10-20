#!/bin/bash
# Verifie la primitive MCP Logging (ctx.info/ctx.debug) de bout en bout,
# via la gateway (JWT reel). Utilise scripts/test_logging.py.
set -e
cd "$(dirname "$0")/.."

echo "--- Mitigation du load-balancer (routage deterministe) ---"
docker compose stop target-server-2
sleep 2

echo "--- Lancement du test (JWT reel) ---"
TOKEN=$(./scripts/keycloak_get_token.sh testuser test1234)
python3 scripts/test_logging.py "http://localhost:9000/mcp" "$TOKEN"

echo "--- Redemarrage de target-server-2 ---"
docker compose start target-server-2
