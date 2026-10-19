#!/bin/bash
# Prepare l'environnement pour la demo 8.4 (consentement Ollama/MCP).
set -e
cd "$(dirname "$0")/.."
echo "--- Arret temporaire de target-server-2 (routage deterministe) ---"
docker compose stop target-server-2
echo ""
echo "--- Prechauffage du modele Ollama ---"
ollama run qwen2.5:3b "dis juste OK" > /dev/null
echo "Pret."
