#!/usr/bin/env python3
"""
Demonstre et verifie un flux OAuth 2.1 Authorization Code + PKCE complet
contre Keycloak, pour le client confidentiel mcp-target-server.

Note technique : Keycloak marque ses cookies de session (AUTH_SESSION_ID,
KC_RESTART, etc.) comme Secure. http.cookiejar les respecte et refuse de
les renvoyer sur une connexion http:// simple (notre environnement de test
local, volontairement sans TLS). On construit donc l'en-tete Cookie a la
main plutot que de laisser cookiejar le faire automatiquement.

Usage :
  python3 scripts/test_pkce_flow.py valid    -> doit reussir (code_verifier correct)
  python3 scripts/test_pkce_flow.py invalid  -> doit echouer (code_verifier errone)
"""
import sys
import re
import hashlib
import base64
import secrets
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar

KEYCLOAK_URL = "http://localhost:8080"
REALM = "mcp-secure-platform"
CLIENT_ID = "mcp-target-server"
CLIENT_SECRET = "R48PxLtdsncHJ19VcOpXxvQ0qVF0mChttVFpjJFBRmxVd1BE1fQQF9gEnbdjUjeSi1i6qAieNUCdv2BNxCBdeY"
REDIRECT_URI = "http://localhost:9999/callback"
USERNAME = "testuser"
PASSWORD = "test1234"

AUTH_ENDPOINT = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/auth"
TOKEN_ENDPOINT = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"


def make_pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    return verifier, challenge


def cookie_header(cj):
    """Construit l'en-tete Cookie a la main (cf. note technique en tete de fichier)."""
    return "; ".join(f"{c.name}={c.value}" for c in cj)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "valid"
    verifier, challenge = make_pkce_pair()
    print(f"code_verifier genere : {verifier[:20]}... ({len(verifier)} caracteres)")
    print(f"code_challenge (S256) : {challenge[:20]}...")

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # 1. GET la page de login, avec le code_challenge dans la requete d'autorisation
    auth_params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{AUTH_ENDPOINT}?{urllib.parse.urlencode(auth_params)}"
    with opener.open(auth_url) as resp:
        html = resp.read().decode("utf-8")

    match = re.search(r'action="([^"]+)"', html)
    if not match:
        print("ERREUR : formulaire de login introuvable dans la page Keycloak.")
        sys.exit(1)
    login_action = match.group(1).replace("&amp;", "&")
    print("Formulaire de login trouve.")

    # 2. POST les identifiants, avec l'en-tete Cookie construit a la main
    login_data = urllib.parse.urlencode({"username": USERNAME, "password": PASSWORD}).encode()
    req = urllib.request.Request(
        login_action,
        data=login_data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie_header(cj),
        },
    )
    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None  # empeche de suivre la redirection vers REDIRECT_URI

    no_redirect_opener = urllib.request.build_opener(NoRedirectHandler)
    final_url = ""
    try:
        with no_redirect_opener.open(req) as resp:
            final_url = resp.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        final_url = e.headers.get("Location", "")

    qs = urllib.parse.urlparse(final_url).query
    params = urllib.parse.parse_qs(qs)
    code = params.get("code", [None])[0]
    error = params.get("error", [None])[0]

    if not code:
        print(f"ERREUR : pas de code recu. error={error} URL finale : {final_url}")
        sys.exit(1)
    print(f"Code d'autorisation recu : {code[:20]}...")

    # 3. Echanger le code contre un token, avec le BON ou un MAUVAIS code_verifier selon le mode
    used_verifier = verifier if mode == "valid" else "verifier-invalide-" + secrets.token_hex(16)
    print(f"Mode : {mode} -> code_verifier utilise : {used_verifier[:20]}...")

    token_data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code_verifier": used_verifier,
    }).encode()

    token_req = urllib.request.Request(TOKEN_ENDPOINT, data=token_data, method="POST")
    try:
        with urllib.request.urlopen(token_req) as resp:
            body = resp.read().decode()
            print("SUCCES : token obtenu.")
            print(body[:200])
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"ECHEC (HTTP {e.code}) : {body}")


if __name__ == "__main__":
    main()
