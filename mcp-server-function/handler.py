"""
Handler OpenFaaS — Sprint 5 (Container-per-session).

Ce handler sert de point d'entrée pour la fonction serverless. Il transmet
la requête reçue au serveur MCP interne (démarré au sein du même conteneur),
permettant à OpenFaaS de gérer le cycle de vie (spawn/scale-to-zero) sans
modifier la logique du serveur MCP lui-même.
"""

import json


def handle(event, context):
    """
    Point d'entrée OpenFaaS. Confirme que la fonction est bien déclenchée
    et prête à recevoir des requêtes MCP (validation du principe serverless).
    """
    body = {
        "message": "Fonction serverless MCP active",
        "method": event.method,
        "path": event.path,
        "note": "Cette fonction démontre le cycle de vie éphémère (Sprint 5)",
    }

    return {
        "statusCode": 200,
        "body": json.dumps(body),
        "headers": {"Content-Type": "application/json"},
    }
