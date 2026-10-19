#!/bin/bash
# Teste la limite du nombre de processus (pids: 256) de target-server-1.
# Redemarre le conteneur avant le test pour repartir d'un etat propre
# (les process sleep du test precedent peuvent rester en zombie et
# saturer artificiellement le cgroup pids).
echo "--- Redemarrage du conteneur pour repartir d'un etat propre ---"
docker restart mcp-target-server-1
sleep 3

echo "######## Test pids : tentative de creer 300 process (limite = 256) ########"
docker exec mcp-target-server-1 python3 -c "
import subprocess
procs = []
try:
    for i in range(300):
        p = subprocess.Popen(['sleep', '2'])
        procs.append(p)
    print('300_PROCESS_CREES')
except Exception as e:
    print(f'ECHEC apres {len(procs)} process : {e}')
"
