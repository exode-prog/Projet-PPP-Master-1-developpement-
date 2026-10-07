#!/bin/bash
# Genere un token d'acces Keycloak pour un utilisateur donne.
# Usage : ./keycloak_get_token.sh [username] [password]
# Par defaut : testuser / test1234
set -e
cd "$(dirname "$0")/.."

REALM="mcp-secure-platform"
CLIENT_SECRET="R48PxLtdsncHJ19VcOpXxvQ0qVF0mChttVFpjJFBRmxVd1BE1fQQF9gEnbdjUjeSi1i6qAieNUCdv2BNxCBdeY"

USERNAME="${1:-testuser}"
PASSWORD="${2:-test1234}"

RESP=$(curl -s -X POST "http://localhost:8080/realms/$REALM/protocol/openid-connect/token" \
  --data-urlencode "client_id=mcp-target-server" \
  --data-urlencode "client_secret=$CLIENT_SECRET" \
  --data-urlencode "grant_type=password" \
  --data-urlencode "username=$USERNAME" \
  --data-urlencode "password=$PASSWORD")

TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "ERREUR : impossible de recuperer le token pour $USERNAME" >&2
  echo "Reponse Keycloak : $RESP" >&2
  exit 1
fi

echo "$TOKEN"
