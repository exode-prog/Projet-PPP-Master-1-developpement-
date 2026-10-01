#!/bin/bash
# teardown.sh — Sprint 5, Tâche 5
# Détruit l'instance de la fonction MCP (scale à zéro), démontrant le
# cycle de vie éphémère du modèle serverless.

set -e

echo "Teardown : arrêt de mcp-server-function..."
kubectl -n openfaas-fn scale deployment mcp-server-function --replicas=0

echo "Vérification (aucun pod ne doit rester) :"
sleep 3
kubectl -n openfaas-fn get pods -l faas_function=mcp-server-function
