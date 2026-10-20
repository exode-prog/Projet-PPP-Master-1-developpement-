"""
Handler OpenFaaS pour mcp-server-function.

Vulnerabilite volontaire (CWE-78, injection de commande) : le parametre
'hostname' recu dans le corps JSON est injecte directement dans une
commande shell, sans validation ni echappement. Meme pattern que
src/vulnerable_server/server.py::ping_host.

Exemple d'exploitation :
    {"hostname": "127.0.0.1; cat /etc/passwd"}
    {"hostname": "127.0.0.1 && whoami"}
    {"hostname": "$(id)"}

Le champ 'pod_hostname' de la reponse identifie le pod Kubernetes qui a
reellement traite la requete.
"""

import json
import socket
import subprocess


def handle(event, context):
    try:
        raw_body = event.body
        if isinstance(raw_body, bytes):
            raw_body = raw_body.decode("utf-8", errors="replace")
        payload = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, AttributeError):
        payload = {}

    hostname = payload.get("hostname", "127.0.0.1")

    # VULNERABILITE : shell=True + concatenation directe = injection de commande
    command = f"ping -c 1 {hostname}"
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=10,
    )

    body = {
        "pod_hostname": socket.gethostname(),
        "command_executed": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }

    return {
        "statusCode": 200,
        "body": json.dumps(body),
        "headers": {"Content-Type": "application/json"},
    }
