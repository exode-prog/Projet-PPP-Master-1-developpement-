#!/bin/bash
# Config "Docker durci SANS gVisor" (seccomp+AppArmor actifs, runtime=runc).
echo "--- Demarrage du conteneur Docker durci (sans gVisor) ---"
docker compose -f docker-compose.vulnerable-seccomp-apparmor-test.yml up -d
sleep 3

echo ""
echo "######## Attaque 1 : lecture de /etc/passwd via injection de commande ########"
python3 /tmp/attack_test.py 8003 "127.0.0.1; cat /etc/passwd"

echo ""
echo "######## Attaque 2 : execution d'un fichier dans /tmp (teste tmpfs:noexec) ########"
python3 /tmp/attack_test.py 8003 "127.0.0.1; echo test > /tmp/x.sh && chmod +x /tmp/x.sh && /tmp/x.sh"

echo ""
echo "--- Arret du conteneur ---"
docker compose -f docker-compose.vulnerable-seccomp-apparmor-test.yml down
