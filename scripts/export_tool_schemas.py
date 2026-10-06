#!/usr/bin/env python3
"""
Exporte les schemas JSON des outils (tools) d'un serveur MCP (Streamable HTTP).
Livrable A.7 du cahier des charges : "les schemas JSON des outils".

Usage:
    python3 scripts/export_tool_schemas.py <URL_MCP> <FICHIER_SORTIE.json> [TOKEN_BEARER]
"""
import sys
import json
import uuid
import urllib.request
import urllib.error


def send_jsonrpc(url, payload, session_id=None, token=None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=15) as resp:
        resp_session_id = resp.headers.get("mcp-session-id") or session_id
        raw = resp.read().decode("utf-8")
        content_type = resp.headers.get("Content-Type", "")

    if "text/event-stream" in content_type or raw.lstrip().startswith("event:") or raw.lstrip().startswith("data:"):
        body = None
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[len("data:"):].strip()
                if not chunk:
                    continue
                try:
                    body = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
        if body is None:
            raise RuntimeError(f"Impossible de parser la reponse SSE:\n{raw}")
        return body, resp_session_id
    else:
        return json.loads(raw), resp_session_id


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    out_path = sys.argv[2]
    token = sys.argv[3] if len(sys.argv) > 3 else None

    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "export_tool_schemas", "version": "1.0"},
        },
    }
    init_result, session_id = send_jsonrpc(url, init_payload, token=token)
    server_info = init_result.get("result", {}).get("serverInfo", {})
    print(f"Connecte a : {server_info.get('name', '?')} (session {session_id})")

    notif_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    try:
        send_jsonrpc(url, notif_payload, session_id=session_id, token=token)
    except Exception:
        pass

    all_tools = []
    cursor = None
    while True:
        params = {"cursor": cursor} if cursor else {}
        list_payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": params,
        }
        list_result, session_id = send_jsonrpc(url, list_payload, session_id=session_id, token=token)
        result = list_result.get("result", {})
        tools = result.get("tools", [])
        all_tools.extend(tools)
        cursor = result.get("nextCursor")
        if not cursor:
            break

    output = {
        "server": server_info,
        "source_url": url,
        "tools": all_tools,
    }

    import os
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"{len(all_tools)} outil(s) exporte(s) vers {out_path}")
    for t in all_tools:
        print(f"  - {t.get('name')}")


if __name__ == "__main__":
    main()
