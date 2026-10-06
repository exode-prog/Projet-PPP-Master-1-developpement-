import asyncio
import json
import os

from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport


async def main():
    url = os.environ.get("TARGET_SERVER_URL", "http://localhost:8010/mcp")
    transport = StreamableHttpTransport(url)
    client = Client(transport)

    async with client:
        tools = await client.list_tools()

        schemas = []
        for tool in tools:
            if hasattr(tool, "model_dump"):
                schemas.append(tool.model_dump(exclude_none=True, mode="json"))
            else:
                schemas.append(
                    {
                        "name": getattr(tool, "name", None),
                        "description": getattr(tool, "description", None),
                        "inputSchema": getattr(tool, "inputSchema", None),
                    }
                )

    output = {
        "project": "Plateforme MCP securisee - Projet PPP Master 1",
        "generatedFrom": url,
        "toolCount": len(schemas),
        "tools": schemas,
    }

    out_path = "schemas/tools.schema.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Fichier ecrit : {out_path}")
    print(f"Nombre d'outils exportes : {len(schemas)}")
    for s in schemas:
        print(f"  - {s.get('name')}")


asyncio.run(main())
