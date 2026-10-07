#!/bin/bash
# Verifie si le conteneur ephemere Lambda (LocalStack) est present.
# C'est un vrai conteneur Docker, donc visible directement via docker ps.
echo "--- Service LocalStack (toujours actif si demarre) ---"
docker ps --filter "name=localstack-mcp$"
echo ""
echo "--- Conteneur Lambda ephemere (present seulement si recemment invoque) ---"
docker ps --filter "name=localstack-mcp-lambda"
