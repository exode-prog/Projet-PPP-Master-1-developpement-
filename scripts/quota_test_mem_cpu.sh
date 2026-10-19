#!/bin/bash
# Teste le depassement memoire (limite 2G) et CPU (limite 1.0) de target-server-1.
echo "######## Test memoire : allocation de 3 Go (limite = 2 Go) ########"
docker exec mcp-target-server-1 python3 -c "
data = bytearray(3 * 1024 * 1024 * 1024)
print('ALLOCATION_REUSSIE')
"
echo "exit code : $?"
docker inspect mcp-target-server-1 --format='OOMKilled: {{.State.OOMKilled}} / Status: {{.State.Status}}'
echo ""

echo "######## Test CPU : boucle de 5 secondes, mesure via docker top ########"
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
