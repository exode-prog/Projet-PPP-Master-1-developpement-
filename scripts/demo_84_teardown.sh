#!/bin/bash
cd "$(dirname "$0")/.."
echo "--- Redemarrage de target-server-2 ---"
docker compose up -d target-server-2
