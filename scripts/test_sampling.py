import asyncio
import sys
import urllib.request
import json

from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

OLLAMA_URL = "http://localhost:11434/api/chat"


def ollama_chat(model, messages):
    payload = {"model": model, "messages": messages, "stream": False}
    req = urllib.request.Request(
        OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=1200) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def main():
    url = sys.argv[1]
    token = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "qwen2.5:3b"

    async def elicitation_handler(message, response_type, params, context):
        print(f"[elicit] {message!r} -> accept")
        return True

    async def sampling_handler(messages, params, context):
        print(f"[SAMPLING DEMANDE PAR LE SERVEUR] {len(messages)} message(s)")
        ollama_messages = []
        if getattr(params, "systemPrompt", None):
            ollama_messages.append({"role": "system", "content": params.systemPrompt})
        for m in messages:
            role = "user" if m.role == "user" else "assistant"
            text = m.content.text if hasattr(m.content, "text") else str(m.content)
            ollama_messages.append({"role": role, "content": text})
        # Appel bloquant execute dans un thread separe pour ne pas geler
        # la boucle asyncio du transport MCP pendant les ~6-7 minutes
        # que prend Ollama sur ce CPU mono-coeur (cf. test direct : 397s
        # de duree Ollama pure pour ce prompt de 537 tokens de contexte).
        result = await asyncio.to_thread(ollama_chat, model, ollama_messages)
        texte = result.get("message", {}).get("content", "")
        print(f"[SAMPLING] Ollama a genere : {texte[:300]}")
        return texte

    transport = StreamableHttpTransport(url, headers={"Authorization": f"Bearer {token}"})
    client = Client(transport, elicitation_handler=elicitation_handler, sampling_handler=sampling_handler)

    async with client:
        r = await client.call_tool("summarize_audit_log", {"last_n": 5}, timeout=1200)
        print("RESULTAT FINAL :", r.data)


asyncio.run(main())
