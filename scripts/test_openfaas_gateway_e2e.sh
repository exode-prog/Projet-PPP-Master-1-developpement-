#!/bin/bash
# Demonstration bout-en-bout - Point jury 3 (integration serverless).
# Chaine : client -> gateway (JWT verifie + quota, REEL) -> fonction OpenFaaS
# mcp-server-function (k3s, runtimeClassName: gvisor) -> attaque
# potentiellement contenue -> trace dans l'audit du gateway.
cd "$(dirname "$0")/.."

echo "######## Demo bout-en-bout - Point jury 3 ########"
echo ""

TOKEN=$(./scripts/keycloak_get_token.sh testuser test1234)
echo "Jeton obtenu (tronque): ${TOKEN:0:40}..."
echo ""

echo "--- Appel normal (baseline) ---"
python3 scripts/call_gateway_function.py "$TOKEN" "127.0.0.1"
echo ""

echo "--- Attaque : lecture de fichier (injection de commande) ---"
python3 scripts/call_gateway_function.py "$TOKEN" '127.0.0.1; cat /etc/passwd'
echo ""

echo "--- Attaque : connexion reseau sortante ---"
python3 scripts/call_gateway_function.py "$TOKEN" '127.0.0.1; python3 -c "import socket;socket.create_connection((\"8.8.8.8\",53),3);print(\"EGRESS_OK\")"'
echo ""

echo "--- Attaque : ecriture + execution dans /tmp ---"
python3 scripts/call_gateway_function.py "$TOKEN" '127.0.0.1; echo "echo PWNED" > /tmp/x.sh && chmod +x /tmp/x.sh && /tmp/x.sh'
echo ""

echo "--- Test du quota (declenchement attendu : 4 appels deja faits ci-dessus) ---"
for i in 1 2 3; do
  echo "  appel supplementaire $i :"
  python3 scripts/call_gateway_function.py "$TOKEN" "127.0.0.1"
done
echo ""

echo "--- Journal d'audit du gateway (dernieres lignes) ---"
docker exec mcp-gateway tail -20 /tmp/gateway_audit.log
echo ""

echo "--- Verification que le stack Docker Compose reste sain ---"
docker ps --format "table {{.Names}}\t{{.Status}}"
