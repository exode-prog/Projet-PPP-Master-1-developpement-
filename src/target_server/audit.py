"""
Module de journalisation (audit) des appels aux outils du serveur MCP (Sprint 2).

Correction Sprint 6 : ce fichier contenait par erreur une copie du code de
auth.py (vérification JWT) depuis le commit initial du Sprint 2 ; la fonction
log_event(), pourtant déjà appelée dans server.py, n'avait jamais été écrite.
Bug latent non détecté jusqu'au relancement du serveur au Sprint 6.

Correction (point jury 1, cdc A.2) : l'identité de l'appelant est maintenant
journalisée. Elle provient du header X-MCP-User, calculé par le gateway à
partir du jeton JWT qu'il a déjà vérifié (preferred_username/sub) — jamais du
jeton brut lui-même, conformément à la règle anti-passthrough (cdc A.6).
"""

import json
import os
from datetime import datetime, timezone

AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "audit.log")


def log_event(tool: str, params: dict, status: str, detail, user: str = "inconnu") -> None:
    """
    Enregistre un événement d'audit pour un appel d'outil.

    tool   : nom de l'outil appelé (ex: "hello", "add")
    params : paramètres fournis par l'appelant
    status : "success" ou "error"
    detail : résultat retourné (succès) ou message d'erreur (échec)
    user   : identité de l'appelant (preferred_username/sub Keycloak), transmise
             par le gateway via le header X-MCP-User. "inconnu" si absent (ex.
             appel direct hors gateway, utilisé pour certains tests techniques).
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "user": user,
        "params": params,
        "status": status,
        "detail": detail,
    }
    line = json.dumps(event, ensure_ascii=False, default=str)

    print(f"[AUDIT] {line}")

    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
