#!/bin/bash
# spawn.sh — Sprint 5, Tâche 5
# Force le démarrage d'une instance de la fonction MCP serverless.

set -e

echo "Spawn : démarrage d'une instance de mcp-server-function..."
kubectl -n openfaas-fn scale deployment mcp-server-function --replicas=1

echo "Attente que le pod soit prêt..."
kubectl -n openfaas-fn wait --for=condition=available --timeout=60s deployment/mcp-server-function

echo "Instance active :"
kubectl -n openfaas-fn get pods -l faas_function=mcp-server-function
