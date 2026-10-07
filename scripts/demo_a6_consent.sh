#!/bin/bash
# Demo A.6 : consentement explicite sur chaque outil.
# hello : consentement accepte -> execution normale.
# list_client_roots : consentement refuse -> operation annulee, aucune execution.
set -e
cd "$(dirname "$0")/.."

REALM="mcp-secure-platform"
CLIENT_SECRET="R48PxLtdsncHJ19VcOpXxvQ0qVF0mChttVFpjJFBRmxVd1BE1fQQF9gEnbdjUjeSi1i6qAieNUCdv2BNxCBdeY"

RESP=$(curl -s -X POST "http://localhost:8080/realms/$REALM/protocol/openid-connect/token" \
  --data-urlencode "client_id=mcp-target-server" --data-urlencode "client_secret=$CLIENT_SECRET" \
  --data-urlencode "grant_type=password" --data-urlencode "username=testuser" --data-urlencode "password=test1234")
TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "--- hello, consentement accepte ---"
for i in 1 2 3; do
  OUT=$(python3 scripts/test_consent.py "http://localhost:9000/mcp" "$TOKEN" "hello" '{"name": "Demo"}' accept 2>&1)
  echo "$OUT"
  echo "$OUT" | grep -q "Session terminated" || break
done

echo ""
echo "--- list_client_roots, consentement refuse ---"
for i in 1 2 3; do
  OUT=$(python3 scripts/test_consent.py "http://localhost:9000/mcp" "$TOKEN" "list_client_roots" '{}' decline 2>&1)
  echo "$OUT"
  echo "$OUT" | grep -q "Session terminated" || break
done
