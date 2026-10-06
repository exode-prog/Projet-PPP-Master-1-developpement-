"""
Serveur MCP de démonstration pour la validation du socle du sprint 1,
enrichi de la sécurité applicative au Sprint 2 (JWT, RBAC, consentement, audit).

Lancement local (stdio, par défaut) :
    python src/target_server/server.py

Lancement en Streamable HTTP (pour accès distant / conteneurisé) :
    MCP_TRANSPORT=http python src/target_server/server.py
"""

import os

from fastmcp import FastMCP, Context
from audit import log_event

mcp = FastMCP(name="Projet master 1 : mcp-secure-platform")

# Identifiant de cette instance (utile uniquement pour demontrer la repartition
# de charge entre plusieurs replicas derriere la gateway, cdc B.4). Sans impact
# fonctionnel : une valeur par defaut est utilisee si la variable n'est pas definie.
INSTANCE_ID = os.environ.get("INSTANCE_ID", "unique")


@mcp.tool()
def hello(name: str = "monde") -> str:
    """Retourne un message de salutation simple. Sert à valider la chaîne MCP de bout en bout."""
    result = f"Bonjour, {name} ! Le serveur MCP fonctionne correctement. (instance: {INSTANCE_ID})"
    log_event("hello", {"name": name}, "success", result)
    return result


@mcp.tool()
async def add(a: float, b: float, ctx: Context) -> float:
    """Additionne deux nombres. Nécessite une confirmation explicite de l'utilisateur avant exécution."""
    result = await ctx.elicit(
        message=f"Confirmer le calcul {a} + {b} = {a + b} ?",
        response_type=bool,
    )

    if result.action != "accept" or not result.data:
        log_event("add", {"a": a, "b": b}, "error", "Consentement refusé")
        raise ValueError("Opération annulée : consentement non accordé par l'utilisateur.")

    computed = a + b
    log_event("add", {"a": a, "b": b}, "success", computed)
    return computed


@mcp.resource("config://server/security-status")
def security_status() -> dict:
    """Expose l'état de sécurité actuel du serveur MCP. Évolue au fil des sprints."""
    return {
        "sandboxed": False,
        "runtime_isolation": "none",
        "network_isolation": "none",
        "note": "Ce serveur n'est pas encore isolé. Sandbox gVisor prévue au Sprint 4.",
        "sprint": 2,
        "auth": "Keycloak OIDC + OAuth 2.1 + PKCE + RBAC (Sprint 2)",
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
