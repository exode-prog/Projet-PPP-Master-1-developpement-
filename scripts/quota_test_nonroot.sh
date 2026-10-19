#!/bin/bash
# Verifie que le conteneur durci tourne avec un utilisateur non privilegie (pas root),
# que son environnement (repertoire personnel, proprietaire des fichiers) est coherent,
# et que le serveur MCP (et son outil ping) fonctionne toujours correctement.
echo "--- Demarrage du conteneur gVisor durci (image non-root 'Fall') ---"
docker compose -f docker-compose.vulnerable-hardened-demo.yml up -d
sleep 8

echo ""
echo "######## Test 1 : utilisateur d'execution dans le conteneur ########"
docker exec mcp-vulnerable-server-HARDENED-DEMO id

echo ""
echo "######## Test 2 : identite et repertoire personnel ########"
docker exec mcp-vulnerable-server-HARDENED-DEMO whoami
docker exec mcp-vulnerable-server-HARDENED-DEMO sh -c 'echo HOME=$HOME'
docker exec mcp-vulnerable-server-HARDENED-DEMO sh -c 'ls -ld $HOME'

echo ""
echo "######## Test 3 : proprietaire des fichiers de l'application ########"
docker exec mcp-vulnerable-server-HARDENED-DEMO ls -la /app

echo ""
echo "######## Test 4 : le serveur MCP fonctionne toujours (ping) ########"
python3 /tmp/attack_test.py 8003 "127.0.0.1"

echo ""
echo "--- Arret du conteneur ---"
docker compose -f docker-compose.vulnerable-hardened-demo.yml down
