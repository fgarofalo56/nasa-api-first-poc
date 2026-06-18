"""MCP smoke client — connects to the running MCP server and calls the tool.

Used by `make demo` to prove an agent gets the SAME governed answer over MCP. Connects
over streamable-http to the server's /mcp endpoint (default the local container port).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = os.environ.get("MCP_URL", "http://localhost:8090/mcp")


async def run() -> int:
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("MCP tools advertised:", [t.name for t in tools.tools])
            result = await session.call_tool(
                "query_supply_risk", {"program": "Artemis-3", "min_delay": 30}
            )
            payload = getattr(result, "structuredContent", None)
            if not payload and result.content:
                block = result.content[0]
                text = getattr(block, "text", None)
                payload = json.loads(text) if text else None
            payload = payload or {}
            materials = payload.get("materials", [])
            print(
                f"MCP tool returned {payload.get('count', len(materials))} material(s); "
                f"correlation-id={payload.get('gateway_correlation_id')}"
            )
            for m in materials:
                print(
                    f"  - {m.get('risk_tier')} risk {m.get('risk_score')}: "
                    f"{m.get('maktx')} (avg delay {m.get('avg_delay_days')}d)"
                )
            return 0 if materials else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
