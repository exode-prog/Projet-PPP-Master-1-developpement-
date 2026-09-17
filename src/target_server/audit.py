"""
Module de validation des JWT émis par Keycloak (Sprint 2 — sécurité applicative).
"""

import os

import jwt
from jwt import PyJWKClient

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "mcp-secure-platform")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "mcp-target-server")

ISSUER = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"

# Le client JWKS met en cache les clés publiques de Keycloak automatiquement
_jwks_client = PyJWKClient(JWKS_URL)


# ---------------------------------------------------------------------------
# RÈGLE DE SÉCURITÉ — Interdiction du token passthrough (cahier des charges A.6)
#
# Les fonctions de ce module valident UNIQUEMENT les tokens reçus par ce
# serveur MCP. Elles ne doivent JAMAIS retransmettre un token reçu vers un
# autre service (API tierce, autre serveur MCP, gateway, etc.).
#
# Si un appel sortant vers un autre service nécessite une authentification,
# ce service doit obtenir SON PROPRE token (ex: via un flow client_credentials
# dédié), jamais réutiliser le token de l'utilisateur final tel quel.
# ---------------------------------------------------------------------------


class TokenValidationError(Exception):
    """Levée quand un token JWT est invalide, expiré, ou mal signé."""
    pass


def verify_token(token: str) -> dict:
    """
    Vérifie la signature et la validité d'un JWT émis par Keycloak.
    Retourne le payload décodé si valide, lève TokenValidationError sinon.
    """
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=ISSUER,
            options={"verify_aud": False},  # simplifié pour le Sprint 2
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenValidationError("Le token a expiré.")
    except jwt.InvalidTokenError as e:
        raise TokenValidationError(f"Token invalide : {e}")


def has_role(payload: dict, required_role: str) -> bool:
    """Vérifie si le token décodé contient le rôle demandé dans realm_access.roles."""
    roles = payload.get("realm_access", {}).get("roles", [])
    return required_role in roles


def require_role(token: str, required_role: str) -> dict:
    """
    Vérifie le token ET le rôle en une seule fonction.
    Retourne le payload si tout est valide, lève TokenValidationError sinon.
    """
    payload = verify_token(token)
    if not has_role(payload, required_role):
        raise TokenValidationError(
            f"Accès refusé : le rôle '{required_role}' est requis."
        )
    return payload
