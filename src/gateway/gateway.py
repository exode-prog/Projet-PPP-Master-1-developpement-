import os
import json
from datetime import datetime, timezone
import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastmcp.server.providers.proxy import FastMCPProxy, ProxyClient
from fastmcp.client.transports.http import StreamableHttpTransport
from fastmcp.client.transports.sse import SSETransport
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware.rate_limiting import SlidingWindowRateLimitingMiddleware, RateLimitError
from fastmcp.server.middleware import Middleware

# --- Backend ciblé par le routage (serveur cible du Sprint 1-2) ---
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000/mcp")

# --- Configuration Keycloak ---
# Deux adresses distinctes sont necessaires car le gateway tourne dans Docker :
# - KEYCLOAK_INTERNAL_URL : adresse joignable DEPUIS le conteneur gateway (nom
#   de service Docker), utilisee uniquement pour recuperer les cles JWKS.
# - KEYCLOAK_PUBLIC_URL : adresse utilisee par les clients EXTERNES (hote,
#   scripts de test) pour obtenir un jeton. C'est cette adresse qui apparait
#   dans le champ "iss" (issuer) du jeton, donc c'est elle qui doit etre
#   utilisee pour la verification de l'issuer, sous peine de rejet systematique
#   ("invalid_token") meme avec un jeton par ailleurs valide.
KEYCLOAK_INTERNAL_URL = os.environ.get("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
KEYCLOAK_PUBLIC_URL = os.environ.get("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "mcp-secure-platform")

ISSUER = f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}"
JWKS_URI = f"{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

# Le gateway vérifie lui-même chaque jeton JWT entrant (signature, expiration,
# issuer) avant de relayer quoi que ce soit au serveur cible. Conformément à la
# règle anti-passthrough (cahier des charges A.6), ce jeton n'est PAS retransmis
# tel quel au backend : seule l'identité vérifiée ici fera foi (quotas, étape 4).
auth = JWTVerifier(
    jwks_uri=JWKS_URI,
    issuer=ISSUER,
    algorithm="RS256",
)

# --- Quotas par identité de client (Sprint 6, Étape 4) ---
# On réutilise le middleware officiel de FastMCP (fenêtre glissante, déjà testé)
# plutôt que de réimplémenter notre propre compteur : moins de code à maintenir,
# même garantie de correction. Compteur en mémoire uniquement : remis à zéro si
# le gateway redémarre (limite assumée, cohérente avec le niveau de simplicité
# du reste du Sprint 6 — voir audit.py).
QUOTA_MAX_CALLS = int(os.environ.get("QUOTA_MAX_CALLS", "5"))
QUOTA_WINDOW_MINUTES = int(os.environ.get("QUOTA_WINDOW_MINUTES", "1"))


def get_client_identity(context) -> str:
    """
    Récupère l'identité du client à partir du jeton JWT déjà vérifié par le gateway
    (JWTVerifier, étape 3). On utilise preferred_username (nom lisible), avec repli
    sur sub (identifiant technique stable) si absent.

    Le paramètre `context` (MiddlewareContext) est imposé par la signature attendue
    par SlidingWindowRateLimitingMiddleware(get_client_id=...), mais n'est pas utilisé
    ici : get_access_token() lit directement le contexte de requête courant.
    """
    token = get_access_token()
    if token is None:
        return "anonyme"
    return token.claims.get("preferred_username") or token.claims.get("sub") or "inconnu"


# Anti-token-passthrough (cahier des charges A.6) : create_proxy() force
# forward_incoming_headers=True, ce qui relaierait tel quel le JWT du client
# vers target-server (jamais verifie la-bas). On construit donc nous-memes
# un ProxyClient, avec forward_incoming_headers=False.
#
# Identite de l'appelant dans l'audit (cahier des charges A.2) : on construit
# un transport ET un dict de headers NEUFS a chaque appel (plutot que de
# reutiliser un client partage via .new(), qui reutilise le MEME objet
# transport -- donc le MEME dict headers -- entre requetes concurrentes :
# risque reel de fuite d'identite entre deux utilisateurs appelant la gateway
# en meme temps). Le header X-MCP-User transmis ici est calcule par le
# gateway a partir du jeton deja verifie (preferred_username/sub) ; ce n'est
# jamais le jeton JWT brut qui est relaye (anti-passthrough toujours respecte).
def _proxy_client_factory():
    identity = get_client_identity(None)
    transport = StreamableHttpTransport(BACKEND_URL, headers={"X-MCP-User": identity})
    transport.forward_incoming_headers = False
    return ProxyClient(transport)

mcp = FastMCPProxy(client_factory=_proxy_client_factory, name="MCP Gateway - Sprint 6", auth=auth)

# --- RBAC : controle d'acces par role (cahier des charges, autorisation) ---
# Le JWTVerifier (ci-dessus) authentifie deja chaque requete (signature, issuer,
# expiration) mais ne restreint rien selon le CONTENU du token. Ce middleware
# ajoute la couche d'autorisation manquante : certains outils exigent un role
# Keycloak precis (realm_access.roles), en plus d'un token simplement valide.
TOOL_ROLE_REQUIREMENTS = {
    "add": "mcp-admin",   # outil sensible : reserve aux utilisateurs avec le role mcp-admin
    # "hello" : pas d'entree -> accessible a tout utilisateur authentifie (mcp-user)
}


class ToolRoleRequirementError(Exception):
    """Levee quand le token authentifie n'a pas le role Keycloak requis pour l'outil demande."""
    pass


class ToolRoleRequirementMiddleware(Middleware):
    """
    Verifie, pour les outils listes dans TOOL_ROLE_REQUIREMENTS, que le token
    JWT deja authentifie par JWTVerifier contient bien le role Keycloak requis.
    """

    async def on_call_tool(self, context, call_next):
        tool_name = context.message.name
        required_role = TOOL_ROLE_REQUIREMENTS.get(tool_name)

        if required_role:
            token = get_access_token()
            roles = token.claims.get("realm_access", {}).get("roles", []) if token else []
            if required_role not in roles:
                identity = get_client_identity(context)
                raise ToolRoleRequirementError(
                    f"Accès refusé : l'outil '{tool_name}' nécessite le rôle "
                    f"'{required_role}' (utilisateur '{identity}' ne le possède pas)."
                )

        return await call_next(context)


mcp.add_middleware(ToolRoleRequirementMiddleware())

# --- Scopes OAuth distincts du RBAC (cahier des charges B.5, Couche 1) ---
# Le role RBAC verifie ci-dessus decrit l'IDENTITE permanente de l'utilisateur
# dans Keycloak. Un scope OAuth decrit, lui, ce que CE JETON PRECIS a ete
# autorise a demander au moment de son emission (parametre scope= de la
# requete de token, cf. scripts/keycloak_init.sh). Les deux controles sont
# volontairement independants : meme un utilisateur avec le role requis se
# voit refuser l'acces si son jeton ne porte pas le scope necessaire (jeton
# obtenu sans le demander explicitement).
TOOL_SCOPE_REQUIREMENTS = {
    "add": "mcp:tools:write",  # outil sensible : exige aussi le scope OAuth mcp:tools:write
}


class ToolScopeRequirementError(Exception):
    """Levee quand le token authentifie n'a pas le scope OAuth requis pour l'outil demande."""
    pass


class ToolScopeRequirementMiddleware(Middleware):
    """
    Verifie, pour les outils listes dans TOOL_SCOPE_REQUIREMENTS, que le token
    JWT deja authentifie porte bien le scope OAuth requis (claim 'scope',
    chaine separee par des espaces, standard OAuth 2.1). Independant du
    controle par role RBAC (ToolRoleRequirementMiddleware ci-dessus) : les
    deux barrieres doivent passer separement.
    """

    async def on_call_tool(self, context, call_next):
        tool_name = context.message.name
        required_scope = TOOL_SCOPE_REQUIREMENTS.get(tool_name)

        if required_scope:
            token = get_access_token()
            granted_scopes = (token.claims.get("scope", "") if token else "").split()
            if required_scope not in granted_scopes:
                identity = get_client_identity(context)
                raise ToolScopeRequirementError(
                    f"Accès refusé : l'outil '{tool_name}' nécessite le scope OAuth "
                    f"'{required_scope}' (jeton de '{identity}' ne le porte pas ; "
                    f"scopes présents : {granted_scopes or ['aucun']})."
                )

        return await call_next(context)


mcp.add_middleware(ToolScopeRequirementMiddleware())

class ToolCallRateLimitingMiddleware(SlidingWindowRateLimitingMiddleware):
    """
    Variante du middleware officiel SlidingWindowRateLimitingMiddleware : au lieu
    de limiter TOUTE requête MCP (y compris le handshake initialize), on ne limite
    que les appels d'outils (tools/call). On réutilise tel quel le compteur par
    identité et la fenêtre glissante hérités ; seul le point d'interception change.
    """

    async def on_request(self, context, call_next):
        return await call_next(context)

    async def on_call_tool(self, context, call_next):
        client_id = await self._get_client_identifier(context)
        limiter = self.limiters[client_id]

        allowed = await limiter.is_allowed()
        if not allowed:
            raise RateLimitError(
                f"Quota dépassé : {self.max_requests} appels d'outils par "
                f"{self.window_seconds // 60} minute(s) pour le client : {client_id}"
            )

        return await call_next(context)


# Instance nommee : reutilisee par la route /invoke-function ci-dessous, pour
# appliquer EXACTEMENT le meme compteur de quota qu'aux outils MCP classiques.
quota_middleware = ToolCallRateLimitingMiddleware(
    max_requests=QUOTA_MAX_CALLS,
    window_minutes=QUOTA_WINDOW_MINUTES,
    get_client_id=get_client_identity,
)
mcp.add_middleware(quota_middleware)

# --- Relais vers la fonction OpenFaaS (integration serverless) ---
# mcp-server-function tourne sous k3s avec runtimeClassName: gvisor. Ce n'est
# pas un serveur MCP (endpoint REST simple), donc le proxy MCP ci-dessus ne
# peut pas la relayer nativement : cette route HTTP dediee applique la meme
# verification JWT et le meme quota qu'un outil MCP, puis relaie vers la
# fonction et trace l'appel dans un journal d'audit dedie au gateway.
GATEWAY_AUDIT_LOG_PATH = os.environ.get("GATEWAY_AUDIT_LOG_PATH", "/tmp/gateway_audit.log")
OPENFAAS_FUNCTION_URL = os.environ.get(
    "OPENFAAS_FUNCTION_URL", "http://172.18.0.1:31112/function/mcp-server-function"
)


def log_gateway_event(action: str, user: str, params: dict, status: str, detail: str) -> None:
    """Journal d'audit cote gateway, distinct de audit.log (target-server)."""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user": user,
        "params": params,
        "status": status,
        "detail": detail,
    }
    try:
        with open(GATEWAY_AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError as e:
        print(f"ERREUR ecriture audit gateway: {e}")


@mcp.custom_route("/invoke-function", methods=["POST"])
async def invoke_function(request: Request) -> JSONResponse:
    """Relaie vers mcp-server-function (gVisor) apres verification JWT + quota."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        log_gateway_event("invoke_openfaas_function", "anonyme", {}, "error",
                           "En-tete Authorization manquant ou mal forme")
        return JSONResponse({"error": "Authorization: Bearer <token> requis"}, status_code=401)

    token_str = auth_header[len("Bearer "):].strip()
    access_token = await auth.verify_token(token_str)
    if access_token is None:
        log_gateway_event("invoke_openfaas_function", "inconnu", {}, "error",
                           "Jeton JWT invalide ou expire")
        return JSONResponse({"error": "jeton JWT invalide ou expire"}, status_code=401)

    identity = (
        access_token.claims.get("preferred_username")
        or access_token.claims.get("sub")
        or "inconnu"
    )

    limiter = quota_middleware.limiters[identity]
    allowed = await limiter.is_allowed()
    if not allowed:
        log_gateway_event("invoke_openfaas_function", identity, {}, "error",
                           f"Quota depasse ({QUOTA_MAX_CALLS}/{QUOTA_WINDOW_MINUTES}min)")
        return JSONResponse({"error": "quota depasse"}, status_code=429)

    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(OPENFAAS_FUNCTION_URL, json=body, timeout=15.0)
        log_gateway_event("invoke_openfaas_function", identity, body, "success",
                           f"HTTP {resp.status_code} depuis la fonction OpenFaaS (gVisor)")
        return JSONResponse(resp.json(), status_code=resp.status_code)
    except Exception as e:
        log_gateway_event("invoke_openfaas_function", identity, body, "error", str(e))
        return JSONResponse({"error": f"echec appel fonction OpenFaaS: {e}"}, status_code=502)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "http")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "9000"))
    mcp.run(transport=transport, host=host, port=port)
