#!/bin/bash
# Demo no-egress reel (cdc B.3/B.5) : compare conteneur durci (internal: true)
# vs conteneur de reference (bridge normal, NAT par defaut).
set -e
cd "$(dirname "$0")/.."

docker compose -f docker-compose.vulnerable-hardened.yml up -d --build
docker compose -f docker-compose.vulnerable.yml up -d --build
sleep 3

echo "--- Conteneur DURCI (attendu : Network is unreachable) ---"
docker exec mcp-vulnerable-server-HARDENED python3 -c "import urllib.request; urllib.request.urlopen('http://1.1.1.1', timeout=3)" 2>&1 | tail -3

echo ""
echo "--- Conteneur de REFERENCE, non durci (attendu : reponse HTTP recue) ---"
docker exec mcp-vulnerable-server-UNSAFE python3 -c "import urllib.request; urllib.request.urlopen('http://1.1.1.1', timeout=3)" 2>&1 | tail -3
