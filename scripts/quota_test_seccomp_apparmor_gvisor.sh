#!/bin/bash
# Config "gVisor durci" (seccomp actif, AppArmor desactive par gVisor - voir chapitre 7).
echo "--- Demarrage du conteneur gVisor durci ---"
docker compose -f docker-compose.vulnerable-hardened-demo.yml up -d
sleep 8

echo ""
echo "######## Attaque 1 : lecture de /etc/passwd via injection de commande ########"
python3 /tmp/attack_test.py 8003 "127.0.0.1; cat /etc/passwd"

echo ""
echo "######## Attaque 2 : execution d'un fichier dans /tmp (teste tmpfs:noexec) ########"
python3 /tmp/attack_test.py 8003 "127.0.0.1; echo test > /tmp/x.sh && chmod +x /tmp/x.sh && /tmp/x.sh"

echo ""
echo "--- Arret du conteneur ---"
docker compose -f docker-compose.vulnerable-hardened-demo.yml down
