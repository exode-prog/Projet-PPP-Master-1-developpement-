"""
SERVEUR MCP VOLONTAIREMENT VULNÉRABLE :  SPRINT 3

Ce serveur contient une injection de commande (RCE) INTRODUITE DÉLIBÉRÉMENT
à des fins pédagogiques et démonstratives, dans le cadre du scénario
"attaque contenue" du cahier des charges (Partie B.2).

NE JAMAIS DÉPLOYER CE CODE EN DEHORS D'UN ENVIRONNEMENT DE LABORATOIRE ISOLÉ.
NE JAMAIS EXPOSER CE SERVEUR SUR UN RÉSEAU PUBLIC OU PARTAGÉ.

Objectif du Sprint 3 : servir de "cobaye" pour valider, au Sprint 4, que
l'isolation gVisor + durcissement contient l'exploitation de cette faille.

Lancement (STRICTEMENT en environnement isolé) :
    python src/vulnerable_server/server.py
"""

import os
import subprocess

from fastmcp import FastMCP

mcp = FastMCP(name="Serveur MCP VULNÉRABLE - Sprint 3 (démo sécurité)")


@mcp.tool()
def ping_host(hostname: str) -> str:
    """
    Fait un ping vers un hôte donné et retourne le résultat.

    VULNÉRABLE : le paramètre 'hostname' est injecté directement dans
    une commande shell, sans aucune validation ni échappement. Un attaquant
    peut y insérer des métacaractères shell (;, &&, |, `, $()) pour exécuter
    des commandes arbitraires sur le système hôte.

    Exemple d'exploitation :
        hostname = "127.0.0.1; cat /etc/passwd"
        hostname = "127.0.0.1 && whoami"
        hostname = "$(id)"
    """
    # VULNÉRABILITÉ : shell=True + concaténation directe = injection de commande
    command = f"ping -c 1 {hostname}"
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout + result.stderr


@mcp.resource("config://server/security-status")
def security_status() -> dict:
    """Expose l'état de sécurité de CE serveur volontairement vulnérable."""
    return {
        "sandboxed": False,
        "runtime_isolation": "none",
        "network_isolation": "none",
        "known_vulnerabilities": ["CWE-78: OS Command Injection (ping_host)"],
        "note": "Serveur INTENTIONNELLEMENT vulnérable — usage Sprint 3/4 uniquement.",
        "sprint": 3,
    }


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "http":
        # SÉCURITÉ : forcé sur 127.0.0.1, jamais 0.0.0.0, pour ce serveur vulnérable.
        # Contrairement au serveur principal, aucune exposition réseau n'est tolérée ici.
        host = "127.0.0.1"
        port = int(os.environ.get("MCP_PORT", "8001"))
        print(" SERVEUR VULNÉRABLE : écoute strictement limitée à 127.0.0.1 ")
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()
