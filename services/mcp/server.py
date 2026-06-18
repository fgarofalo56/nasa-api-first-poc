"""MCP server — exposes the governed supply-risk query as an agent tool.

One tool, `query_supply_risk`, lets an MCP host (Claude Desktop, Copilot, Foundry, …)
answer the Artemis supply-chain question by reaching the *governed gateway surface* —
it fetches a bearer token from the local issuer and calls Kong, never the database.

Transports:
  * streamable-http (default) on MCP_PORT — how the container runs; also serves /healthz
  * stdio (MCP_TRANSPORT=stdio) — how a desktop MCP host launches it locally
"""

from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

KONG_URL = os.environ.get("KONG_INTERNAL_URL", "http://kong:8000").rstrip("/")
IDENTITY_URL = os.environ.get("IDENTITY_INTERNAL_URL", "http://identity:8081").rstrip("/")
CONSUMER = os.environ.get("MCP_CONSUMER", "artemis-agent")
PORT = int(os.environ.get("MCP_PORT", "8090"))

mcp = FastMCP("artemis-supply-chain", host="0.0.0.0", port=PORT)


def _token(client: httpx.Client) -> str:
    resp = client.post(f"{IDENTITY_URL}/token", json={"consumer": CONSUMER}, timeout=10)
    resp.raise_for_status()
    return resp.json()["access_token"]


@mcp.tool()
def query_supply_risk(
    program: str = "Artemis-3",
    min_delay: int = 30,
    criticality: str = "Critical",
    sole_source_only: bool = True,
) -> dict:
    """Find high supply-risk materials for an Artemis program, through the gateway.

    Answers questions like "which Critical, sole-source materials on Artemis-3 have an
    average delay > 30 days?". The call is authenticated, rate-limited, and metered by
    Kong; the data never leaves Postgres.

    Args:
        program: Artemis program (e.g. "Artemis-3", "Gateway", "Moon-Base").
        min_delay: minimum average delay in days (exclusive).
        criticality: "Critical" | "Essential" | "Routine"; empty string for any.
        sole_source_only: restrict to single-source materials.
    """
    clauses = [f"program eq '{program}'", f"avg_delay_days gt {min_delay}"]
    if criticality:
        clauses.append(f"criticality eq '{criticality}'")
    if sole_source_only:
        clauses.append("sole_source eq true")
    flt = " and ".join(clauses)
    url = f"{KONG_URL}/api/SupplyRisk?$filter={flt}&$orderby=risk_score desc"
    with httpx.Client() as client:
        token = _token(client)
        resp = client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        resp.raise_for_status()
        rows = resp.json().get("value", [])
        corr = resp.headers.get("X-Correlation-ID")
    return {
        "question": (
            f"{criticality or 'any'} "
            f"{'sole-source' if sole_source_only else 'any-sourcing'} materials on "
            f"{program} with average delay > {min_delay} days"
        ),
        "consumer": CONSUMER,
        "gateway_correlation_id": corr,
        "count": len(rows),
        "materials": rows,
        "note": "Answered through the Kong gateway; data never left Postgres.",
    }


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    mcp.run(transport=os.environ.get("MCP_TRANSPORT", "streamable-http"))
