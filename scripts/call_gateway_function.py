#!/usr/bin/env python3
"""
Appelle la route /invoke-function du gateway (point jury 3), avec un jeton
JWT optionnel et un hostname (payload) pour la fonction OpenFaaS.
Usage: python3 call_gateway_function.py <token_ou_vide> <hostname_payload>
"""
import sys
import json
import urllib.request
import urllib.error

GATEWAY_URL = "http://localhost:9000/invoke-function"


def main():
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    hostname = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps({"hostname": hostname}).encode()
    req = urllib.request.Request(GATEWAY_URL, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print("HTTP", resp.status)
            print(resp.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP", e.code)
        print(e.read().decode())
    except Exception as e:
        print("ERREUR:", e)


if __name__ == "__main__":
    main()
