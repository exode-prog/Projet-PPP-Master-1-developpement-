import asyncio
import sys

import mcp.types as types
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport


async def main():
    url = sys.argv[1]
    token = sys.argv[2]

    transport = StreamableHttpTransport(url, headers={"Authorization": f"Bearer {token}"})
    client = Client(transport)

    ref = types.ResourceTemplateReference(
        type="ref/resource", uri="config://server/{section}"
    )

    async with client:
        print("--- Completion pour value='sec' (doit matcher security-status) ---")
        comp1 = await client.complete(ref=ref, argument={"name": "section", "value": "sec"})
        print("values:", comp1.values, "total:", comp1.total, "hasMore:", comp1.hasMore)

        print("--- Completion pour value='v' (doit matcher version) ---")
        comp2 = await client.complete(ref=ref, argument={"name": "section", "value": "v"})
        print("values:", comp2.values, "total:", comp2.total, "hasMore:", comp2.hasMore)

        print("--- Completion pour value='' (doit matcher les deux) ---")
        comp3 = await client.complete(ref=ref, argument={"name": "section", "value": ""})
        print("values:", comp3.values, "total:", comp3.total, "hasMore:", comp3.hasMore)


asyncio.run(main())
