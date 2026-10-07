#!/bin/bash
# Verifie si le pod OpenFaaS mcp-server-function est actif.
# Ce n'est PAS un conteneur Docker direct (c'est un Pod Kubernetes gere par k3s),
# donc "docker ps" ne le montrera jamais : il faut passer par kubectl.
kubectl -n openfaas-fn get pods -l faas_function=mcp-server-function
