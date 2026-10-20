#!/bin/bash
# Verifie que l'identite de l'appelant apparait dans le journal d'audit
# (point jury 1, cdc A.2). Arrete temporairement target-server-2 pour un
# routage deterministe (limitation d'affinite de session deja documentee,
# cf. Etape 4bis du README).
set -e
cd "$(dirname "$0")/.."

echo "--- Arret temporaire de target-server-2 (routage deterministe) ---"
docker compose stop target-server-2

TOKEN=$(./scripts/keycloak_get_token.sh)
echo ""
echo "--- Appel de hello par testuser ---"
python3 scripts/test_consent.py "http://localhost:9000/mcp" "$TOKEN" "hello" '{"name": "AuditTest"}' accept

echo ""
echo "--- Dernieres lignes du journal d'audit ---"
docker exec mcp-target-server-1 tail -n 5 /app/audit.log

echo ""
echo "--- Redemarrage de target-server-2 ---"
docker compose up -d target-server-2
