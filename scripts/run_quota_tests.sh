#!/bin/bash
# Teste les 3 limites déclarées dans docker-compose.yml pour target-server-1 :
# cpus: "1.0", memory: 2G, pids: 256.
cd "$(dirname "$0")/.."

echo "######## 1. Limites vues par le cgroup du conteneur ########"
docker exec mcp-target-server-1 sh -c "echo mem:; cat /sys/fs/cgroup/memory.max; echo cpu:; cat /sys/fs/cgroup/cpu.max; echo pids:; cat /sys/fs/cgroup/pids.max"
echo ""

echo "######## 2. Test memoire : tentative d'allocation de 3 Go (limite = 2 Go) ########"
docker exec mcp-target-server-1 python3 -c "
data = bytearray(3 * 1024 * 1024 * 1024)
print('ALLOCATION_REUSSIE')
"
echo "exit code : $?"
docker inspect mcp-target-server-1 --format='OOMKilled: {{.State.OOMKilled}} / Status: {{.State.Status}}'
echo ""

echo "######## 3. Test CPU : boucle infinie 5 secondes, mesure via docker top ########"
docker exec -d mcp-target-server-1 python3 -c "
import time
end = time.time() + 5
while time.time() < end:
    pass
"
sleep 2
echo "-- Charge CPU mesurée (docker top, colonne C) --"
docker top mcp-target-server-1
sleep 4
echo ""

echo "######## 4. Test pids : tentative de creer 300 process (limite = 256) ########"
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
