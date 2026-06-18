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


@mcp.tool()
def material_detail(material: str) -> dict:
    """Full governed record for ONE material — risk, recent purchase orders, and supplier.

    Accepts an NSN material number (e.g. "NSN-4002-901834") or a name fragment
    (e.g. "battery module"). Composes several gateway calls (SupplyRisk -> PurchaseOrder
    -> Vendor); net price/value + unit cost are redacted at the gateway. Data never
    leaves Postgres.
    """
    is_nsn = material.strip().upper().startswith("NSN-")
    with httpx.Client() as client:
        token = _token(client)
        hdr = {"Authorization": f"Bearer {token}"}
        if is_nsn:
            rk = client.get(
                f"{KONG_URL}/api/SupplyRisk/matnr/{material.strip()}", headers=hdr, timeout=20
            )
            rk.raise_for_status()
            corr = rk.headers.get("X-Correlation-ID")
            body = rk.json()
            risk_rows = body.get("value", [body] if body and "matnr" in body else [])
        else:
            # DAB doesn't support OData contains(); fetch the highest-risk page (the
            # materials a supply-risk question is about) and match the name client-side.
            rk = client.get(
                f"{KONG_URL}/api/SupplyRisk?$orderby=risk_score desc&$first=200",
                headers=hdr,
                timeout=20,
            )
            rk.raise_for_status()
            corr = rk.headers.get("X-Correlation-ID")
            term = material.strip().lower()
            risk_rows = [
                r for r in rk.json().get("value", []) if term in str(r.get("maktx", "")).lower()
            ]
        if not risk_rows:
            return {
                "found": False,
                "query": material,
                "gateway_correlation_id": corr,
                "note": "No matching material in the governed supply-risk product.",
            }
        risk = risk_rows[0]
        matnr = risk["matnr"]
        pos = client.get(
            f"{KONG_URL}/api/PurchaseOrder?$filter=matnr eq '{matnr}'&$orderby=delay_days desc&$first=5",
            headers=hdr,
            timeout=20,
        )
        po_rows = pos.json().get("value", []) if pos.status_code == 200 else []
        vendor = None
        if po_rows:
            vr = client.get(
                f"{KONG_URL}/api/Vendor/lifnr/{po_rows[0].get('lifnr')}", headers=hdr, timeout=20
            )
            if vr.status_code == 200:
                vv = vr.json()
                vlist = vv.get("value", [vv] if "lifnr" in vv else [])
                vendor = vlist[0] if vlist else None
    return {
        "found": True,
        "material_id": matnr,
        "material_name": risk.get("maktx"),
        "program": risk.get("program"),
        "criticality": risk.get("criticality"),
        "risk_tier": risk.get("risk_tier"),
        "risk_score": risk.get("risk_score"),
        "avg_delay_days": risk.get("avg_delay_days"),
        "sole_source": risk.get("sole_source"),
        "supplier": (vendor or {}).get("name1"),
        "cage_code": (vendor or {}).get("cage_code"),
        "recent_pos": po_rows,
        "gateway_correlation_id": corr,
        "note": "Composed from SupplyRisk -> PurchaseOrder -> Vendor through the gateway; cost fields redacted.",
    }


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    mcp.run(transport=os.environ.get("MCP_TRANSPORT", "streamable-http"))
