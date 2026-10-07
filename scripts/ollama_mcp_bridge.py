#!/usr/bin/env python3
"""
Pont Ollama <-> MCP gateway securise.

Contrairement a `ollmcp`, ce script gere reellement les primitives MCP
Elicitation (consentement A.6, validation humaine explicite dans le terminal)
et Sampling (en redemandant a Ollama de generer le texte demande).

Usage:
    python3 scripts/ollama_mcp_bridge.py "<url du gateway>" "<token>" "<requete en langage naturel>" [modele]

Exemple:
    TOKEN=$(...)
    python3 scripts/ollama_mcp_bridge.py "http://localhost:9000/mcp" "$TOKEN" \
        "utilise l'outil add pour calculer 5 + 4" qwen2.5:3b
"""
import asyncio
import json
import sys
import urllib.request

from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

OLLAMA_URL = "http://localhost:11434/api/chat"


def ollama_chat(model, messages, tools=None):
    """Appelle l'API locale d'Ollama (aucune dependance externe, juste stdlib)."""
    payload = {"model": model, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8"))


def mcp_tool_to_ollama_tool(mcp_tool):
    """Convertit un outil MCP (fastmcp) au format 'tools' attendu par Ollama."""
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "parameters": mcp_tool.inputSchema or {"type": "object", "properties": {}},
        },
    }


async def elicitation_handler(message, response_type, params, context):
    """Primitive Elicitation : on demande une vraie validation humaine au terminal."""
    print(f"\n[CONSENTEMENT REQUIS] {message}")
    reponse = input("Confirmer cette action ? (o/n) : ").strip().lower()
    return reponse in ("o", "oui", "y", "yes")


def make_sampling_handler(model):
    """Primitive Sampling : le serveur demande au client de faire generer du texte
    par SON LLM local. On redemande donc a Ollama (sans les outils MCP cette fois,
    juste une generation de texte simple)."""

    async def sampling_handler(messages, params, context):
        print(f"\n[SAMPLING DEMANDE PAR LE SERVEUR] {len(messages)} message(s) a traiter")
        ollama_messages = []
        if getattr(params, "systemPrompt", None):
            ollama_messages.append({"role": "system", "content": params.systemPrompt})
        for m in messages:
            role = "user" if m.role == "user" else "assistant"
            text = m.content.text if hasattr(m.content, "text") else str(m.content)
            ollama_messages.append({"role": role, "content": text})

        result = ollama_chat(model, ollama_messages)
        texte = result.get("message", {}).get("content", "")
        print(f"[SAMPLING] Ollama a genere : {texte[:200]}")
        return texte

    return sampling_handler


async def main():
    if len(sys.argv) < 4:
        print("Usage: ollama_mcp_bridge.py <url_gateway> <token> <requete> [modele]")
        sys.exit(1)

    url = sys.argv[1]
    token = sys.argv[2]
    requete = sys.argv[3]
    modele = sys.argv[4] if len(sys.argv) > 4 else "qwen2.5:3b"

    transport = StreamableHttpTransport(url, headers={"Authorization": f"Bearer {token}"})
    client = Client(
        transport,
        elicitation_handler=elicitation_handler,
        sampling_handler=make_sampling_handler(modele),
    )

    async with client:
        mcp_tools = await client.list_tools()
        ollama_tools = [mcp_tool_to_ollama_tool(t) for t in mcp_tools]
        print(f"Outils MCP disponibles : {[t.name for t in mcp_tools]}")

        messages = [{"role": "user", "content": requete}]
        print(f"\nEnvoi a Ollama ({modele})...")
        result = ollama_chat(modele, messages, tools=ollama_tools)
        msg = result.get("message", {})

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            print("\nOllama n'a pas demande d'outil, reponse directe :")
            print(msg.get("content", ""))
            return

        for tc in tool_calls:
            fn = tc.get("function", {})
            nom_outil = fn.get("name")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            print(f"\nOllama demande d'appeler : {nom_outil}({args})")
            try:
                r = await client.call_tool(nom_outil, args)
                print(f"RESULTAT : {r.data}")
            except Exception as e:
                print(f"ERREUR : {e}")


asyncio.run(main())
