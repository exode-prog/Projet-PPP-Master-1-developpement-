"""
Module de journalisation (audit) des appels aux outils du serveur MCP (Sprint 2).

Correction Sprint 6 : ce fichier contenait par erreur une copie du code de
auth.py (vérification JWT) depuis le commit initial du Sprint 2 ; la fonction
log_event(), pourtant déjà appelée dans server.py, n'avait jamais été écrite.
Bug latent non détecté jusqu'au relancement du serveur au Sprint 6.

Limite actuelle assumée : journalise l'outil, les paramètres, le statut et le
résultat de chaque appel, mais pas encore l'identité de l'appelant (le jeton
JWT n'est pas encore vérifié au sein de l'exécution des outils eux-mêmes).
"""

import json
import os
from datetime import datetime, timezone

AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "audit.log")


def log_event(tool: str, params: dict, status: str, detail) -> None:
    """
    Enregistre un événement d'audit pour un appel d'outil.

    tool   : nom de l'outil appelé (ex: "hello", "add")
    params : paramètres fournis par l'appelant
    status : "success" ou "error"
    detail : résultat retourné (succès) ou message d'erreur (échec)
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "params": params,
        "status": status,
        "detail": detail,
    }
    line = json.dumps(event, ensure_ascii=False, default=str)

    print(f"[AUDIT] {line}")

    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
