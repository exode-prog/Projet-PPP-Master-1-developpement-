"""
Serveur MCP de démonstration pour la validation du socle du sprint 1.
Ce serveur expose 2 outils (Tools), 1 Resource et 1 Prompt via FastMCP,
pour valider que la chaîne complète fonctionne :
FastMCP -> MCP Inspector -> Ollama.

Lancement local (stdio, par défaut) :
    python src/target_server/server.py

Lancement en Streamable HTTP (pour accès distant / conteneurisé) :
    MCP_TRANSPORT=http python src/target_server/server.py
"""

import os

from fastmcp import FastMCP

mcp = FastMCP(name="Projet master 1 : mcp-secure-platform")


@mcp.tool()
def hello(name: str = "monde") -> str:
    """Retourne un message de salutation simple. Sert à valider la chaîne MCP de bout en bout."""
    return f"Bonjour, {name} ! Le serveur MCP fonctionne correctement."


@mcp.tool()
def add(a: float, b: float) -> float:
    """Additionne deux nombres. Outil de test basique pour vérifier les paramètres typés."""
    return a + b


@mcp.resource("config://server/security-status")
def security_status() -> dict:
    """Expose l'état de sécurité actuel du serveur MCP. Évolue au fil des sprints."""
    return {
        "sandboxed": False,
        "runtime_isolation": "none",
        "network_isolation": "none",
        "note": "Ce serveur n'est pas encore isolé. Sandbox gVisor prévue au Sprint 4.",
        "sprint": 1,
    }


@mcp.prompt()
def analyser_securite() -> str:
    """Prompt préconfiguré pour demander une analyse du statut de sécurité du serveur."""
    return (
        "Consulte la resource config://server/security-status de ce serveur MCP, "
        "puis analyse son niveau de sécurité actuel. Indique clairement : "
        "1) si le serveur est isolé ou non, "
        "2) les risques associés à son état actuel, "
        "3) ce qui doit être fait pour le sécuriser."
    )


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "http":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8000"))
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()
