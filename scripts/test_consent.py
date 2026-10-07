import asyncio
import sys
import json

from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport


async def main():
    url = sys.argv[1]
    token = sys.argv[2]
    tool_name = sys.argv[3]
    args = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
    accept = (sys.argv[5].lower() != "decline") if len(sys.argv) > 5 else True

    async def elicitation_handler(message, response_type, params, context):
        print(f"[elicit] {message!r} -> {'accept' if accept else 'decline'}")
        return accept

    transport = StreamableHttpTransport(url, headers={"Authorization": f"Bearer {token}"})
    client = Client(transport, elicitation_handler=elicitation_handler)

    async with client:
        await client.list_tools()
        try:
            r = await client.call_tool(tool_name, args)
            print("RESULTAT :", r.data)
        except Exception as e:
            print("ERREUR :", e)


asyncio.run(main())
