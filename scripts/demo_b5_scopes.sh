#!/bin/bash
# Demo B.5 : scopes OAuth distincts du RBAC.
# adminuser (role mcp-admin) est refuse sur "add" sans le scope mcp:tools:write,
# puis accepte quand son jeton porte explicitement ce scope. Meme role, resultat
# different selon le scope du jeton : preuve de l'independance des 2 controles.
set -e
cd "$(dirname "$0")/.."

REALM="mcp-secure-platform"
CLIENT_SECRET="R48PxLtdsncHJ19VcOpXxvQ0qVF0mChttVFpjJFBRmxVd1BE1fQQF9gEnbdjUjeSi1i6qAieNUCdv2BNxCBdeY"

echo "--- Test 1 : adminuser SANS scope mcp:tools:write (attendu : refus) ---"
RESP=$(curl -s -X POST "http://localhost:8080/realms/$REALM/protocol/openid-connect/token" \
  --data-urlencode "client_id=mcp-target-server" --data-urlencode "client_secret=$CLIENT_SECRET" \
  --data-urlencode "grant_type=password" --data-urlencode "username=adminuser" --data-urlencode "password=admin1234")
TOKEN_NOSCOPE=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
python3 scripts/test_add_with_scope.py "http://localhost:9000/mcp" "$TOKEN_NOSCOPE"

echo ""
echo "--- Test 2 : adminuser AVEC scope mcp:tools:write (attendu : succes) ---"
for i in 1 2 3; do
  RESP2=$(curl -s -X POST "http://localhost:8080/realms/$REALM/protocol/openid-connect/token" \
    --data-urlencode "client_id=mcp-target-server" --data-urlencode "client_secret=$CLIENT_SECRET" \
    --data-urlencode "grant_type=password" --data-urlencode "username=adminuser" --data-urlencode "password=admin1234" \
    --data-urlencode "scope=openid mcp:tools:write")
  TOKEN_SCOPE=$(echo "$RESP2" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
  OUT=$(python3 scripts/test_add_with_scope.py "http://localhost:9000/mcp" "$TOKEN_SCOPE" 2>&1)
  echo "$OUT"
  echo "$OUT" | grep -q "Session terminated" || break
done
