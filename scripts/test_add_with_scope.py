import asyncio
import sys

from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport


async def main():
    url = sys.argv[1]
    token = sys.argv[2]

    async def elicitation_handler(message, response_type, params, context):
        print(f"[elicit] {message!r} -> accept")
        return True

    transport = StreamableHttpTransport(url, headers={"Authorization": f"Bearer {token}"})
    client = Client(transport, elicitation_handler=elicitation_handler)

    async with client:
        await client.list_tools()
        try:
            r = await client.call_tool("add", {"a": 2, "b": 3})
            print("RESULTAT :", r.data)
        except Exception as e:
            print("ERREUR :", e)


asyncio.run(main())
