#!/bin/bash
# Affiche les limites réellement vues par le conteneur target-server-1,
# a comparer avec les valeurs declarees dans docker-compose.yml
# (cpus: "1.0", memory: 2G, pids: 256).
echo "--- Limites vues par le cgroup du conteneur ---"
docker exec mcp-target-server-1 sh -c "echo memory.max:; cat /sys/fs/cgroup/memory.max; echo cpu.max:; cat /sys/fs/cgroup/cpu.max; echo pids.max:; cat /sys/fs/cgroup/pids.max"
