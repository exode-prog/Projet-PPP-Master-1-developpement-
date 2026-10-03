import os
from fastmcp.server import create_proxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware.rate_limiting import SlidingWindowRateLimitingMiddleware, RateLimitError

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


mcp = create_proxy(BACKEND_URL, name="MCP Gateway - Sprint 6", auth=auth)

class ToolCallRateLimitingMiddleware(SlidingWindowRateLimitingMiddleware):
    """
    Variante du middleware officiel SlidingWindowRateLimitingMiddleware : au lieu
    de limiter TOUTE requête MCP (y compris le handshake initialize), on ne limite
    que les appels d'outils (tools/call). On réutilise tel quel le compteur par
    identité et la fenêtre glissante hérités ; seul le point d'interception change.
    """

    async def on_request(self, context, call_next):
        # On laisse passer sans comptage : initialize, notifications, listes, etc.
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


mcp.add_middleware(
    ToolCallRateLimitingMiddleware(
        max_requests=QUOTA_MAX_CALLS,
        window_minutes=QUOTA_WINDOW_MINUTES,
        get_client_id=get_client_identity,
    )
)

if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "http")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "9000"))
    mcp.run(transport=transport, host=host, port=port)
