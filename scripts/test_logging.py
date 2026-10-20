#!/usr/bin/env python3
"""
Verifie la primitive MCP Logging (ctx.info/ctx.debug dans server.py).
hello() exige aussi un consentement explicite (ctx.elicit, cdc A.6) :
on l'accepte automatiquement ici pour atteindre le point qui emet le log.
Usage: python3 test_logging.py <gateway_url> <token>
"""
import asyncio
import sys
from fastmcp.client import Client
from fastmcp.client.transports.http import StreamableHttpTransport

GATEWAY_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9000/mcp"
TOKEN = sys.argv[2] if len(sys.argv) > 2 else ""

received = []


async def log_handler(params):
    received.append(params)
    print(f"[LOG RECU] level={params.level} logger={params.logger} data={params.data}")


async def elicitation_handler(message, response_type, params, context):
    print(f"[ELICITATION] {message!r} -> accepte automatiquement")
    return True


async def main():
    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    transport = StreamableHttpTransport(GATEWAY_URL, headers=headers)
    async with Client(
        transport,
        log_handler=log_handler,
        elicitation_handler=elicitation_handler,
    ) as client:
        tools = await client.list_tools()
        print("Outils vus:", [t.name for t in tools])
        result = await client.call_tool("hello", {"name": "LoggingTest"})
        print("Resultat outil:", result.data if hasattr(result, "data") else result)

    print(f"\nTotal notifications de log recues: {len(received)}")
    if not received:
        print("AUCUNE notification recue -> la primitive Logging n'est pas relayee correctement.")


if __name__ == "__main__":
    asyncio.run(main())
