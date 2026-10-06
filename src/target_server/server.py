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
from mcp.types import Completion, ResourceTemplateReference
from audit import log_event

mcp = FastMCP(name="Projet master 1 : mcp-secure-platform")

# Identifiant de cette instance (utile uniquement pour demontrer la repartition
# de charge entre plusieurs replicas derriere la gateway, cdc B.4). Sans impact
# fonctionnel : une valeur par defaut est utilisee si la variable n'est pas definie.
INSTANCE_ID = os.environ.get("INSTANCE_ID", "unique")


@mcp.tool()
async def hello(ctx: Context, name: str = "monde") -> str:
    """Retourne un message de salutation simple. Sert à valider la chaîne MCP de bout en bout."""
    # Primitive Logging (A.2, cdc) : message envoye au client pendant l'execution,
    # distinct du journal d'audit applicatif (audit.py) qui reste cote serveur.
    await ctx.info(f"Appel de l'outil hello avec name={name!r}")
    result = f"Bonjour, {name} ! Le serveur MCP fonctionne correctement. (instance: {INSTANCE_ID})"
    log_event("hello", {"name": name}, "success", result)
    return result


@mcp.tool()
async def add(a: float, b: float, ctx: Context) -> float:
    """Additionne deux nombres. Nécessite une confirmation explicite de l'utilisateur avant exécution."""
    await ctx.debug(f"Demande de consentement pour {a} + {b}")
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


# Resource template parametree (au lieu d'une URI fixe) pour demontrer la
# primitive Completions (A.2, cdc) : le client peut demander au serveur les
# valeurs possibles de {section} via mcp._mcp_server.completion() ci-dessous.
_CONFIG_SECTIONS = {
    "security-status": {
        "runtime_isolation": "aucune sur ce composant (axe 3) ; gVisor demontre separement sur l'axe 1 (vulnerable_server)",
        "network_isolation": "reseau Docker interne mcp-net, pas d'exposition directe de target-server",
        "auth": "Keycloak OIDC + OAuth 2.1 + PKCE + RBAC",
        "token_passthrough": "desactive (anti-pattern cdc A.6 corrige)",
        "audit": "journal d'audit actif (audit.py)",
    },
    "version": {
        "instance_id": INSTANCE_ID,
        "fastmcp": "3.4.8",
    },
}


@mcp.resource("config://server/{section}")
def server_config(section: str) -> dict:
    """Expose la configuration/etat du serveur MCP pour une section donnee (security-status, version)."""
    if section not in _CONFIG_SECTIONS:
        return {"error": f"section inconnue : {section}", "sections_disponibles": list(_CONFIG_SECTIONS.keys())}
    return _CONFIG_SECTIONS[section]


@mcp.tool()
async def summarize_audit_log(ctx: Context, last_n: int = 5) -> str:
    """Resume les dernieres entrees du journal d'audit via le LLM de l'hote (primitive Sampling, A.2 cdc)."""
    await ctx.info(f"Lecture des {last_n} dernieres entrees de audit.log pour resume (Sampling)")
    audit_path = os.environ.get("AUDIT_LOG_PATH", "audit.log")
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-last_n:]
    except FileNotFoundError:
        lines = []

    if not lines:
        return "Aucune entree d'audit disponible pour le moment."

    raw_log = "".join(lines)
    result = await ctx.sample(
        messages=(
            "Resume en une ou deux phrases ces entrees de journal d'audit MCP "
            f"(une entree JSON par ligne) :\n{raw_log}"
        ),
        system_prompt="Tu es un assistant de securite qui resume des journaux d'audit de facon concise et factuelle.",
        max_tokens=200,
    )
    return result.text


@mcp.tool()
async def list_client_roots(ctx: Context) -> list[str]:
    """Liste les repertoires racines (roots) que le client MCP a declares comme accessibles (primitive Roots, A.2 cdc)."""
    await ctx.debug("Demande de la liste des roots au client")
    roots = await ctx.list_roots()
    return [str(r.uri) for r in roots]


@mcp._mcp_server.completion()
async def handle_completion(ref, argument, completion_context):
    """Fournit l'autocompletion pour le parametre {section} de la resource config://server/{section} (primitive Completions, A.2 cdc)."""
    if isinstance(ref, ResourceTemplateReference) and ref.uri == "config://server/{section}":
        if argument.name == "section":
            sections = list(_CONFIG_SECTIONS.keys())
            matches = [s for s in sections if s.startswith(argument.value)]
            return Completion(values=matches, total=len(matches), hasMore=False)
    return None


@mcp.prompt()
def analyser_securite() -> str:
    """Prompt préconfiguré pour demander une analyse du statut de sécurité du serveur."""
    return (
        "Consulte la resource config://server/security-status de ce serveur MCP (section 'security-status'), "
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
