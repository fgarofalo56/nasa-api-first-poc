"""Stand-in for an *existing* DAB API (the DOT transportation demo).

This is a second, independent data source — a DOT-flavored bridge-condition dataset
exposed with a DAB-style REST surface (`/api/openapi`, `/api/Bridge` with OData-ish
`$filter`/`$orderby`/`$first`/`$select`). It lives ONLY on the internal network, so the
only way to reach it is through Kong — exactly like the Artemis system of record.

In the demo the onboarding wizard registers this upstream with the gateway at runtime,
showing how a new source is published through Kong without touching the source itself.
The same wizard step targets the real published DOT DAB URL when it is online (see
docs/ADD-A-SOURCE.md). Synthetic data only.
"""

from __future__ import annotations

import os
import re

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

PORT = int(os.environ.get("TRANSPORT_PORT", "8200"))

app = FastAPI(title="DOT Transportation (DAB-style) source", version="0.1.0")

# Synthetic National Bridge Inventory-style records (clearly synthetic).
BRIDGES = [
    {
        "bridge_id": "DOT-0001",
        "name": "Cascade River Crossing (SYNTHETIC)",
        "state": "WA",
        "year_built": 1971,
        "condition_rating": 4,
        "avg_daily_traffic": 48000,
        "deck_area_sqm": 5200,
        "status": "Structurally Deficient",
    },
    {
        "bridge_id": "DOT-0002",
        "name": "Granite Gorge Viaduct (SYNTHETIC)",
        "state": "CO",
        "year_built": 1985,
        "condition_rating": 6,
        "avg_daily_traffic": 22000,
        "deck_area_sqm": 3100,
        "status": "Fair",
    },
    {
        "bridge_id": "DOT-0003",
        "name": "Meridian Bay Bridge (SYNTHETIC)",
        "state": "FL",
        "year_built": 1962,
        "condition_rating": 3,
        "avg_daily_traffic": 91000,
        "deck_area_sqm": 12800,
        "status": "Structurally Deficient",
    },
    {
        "bridge_id": "DOT-0004",
        "name": "Polaris Interchange (SYNTHETIC)",
        "state": "OH",
        "year_built": 2004,
        "condition_rating": 8,
        "avg_daily_traffic": 64000,
        "deck_area_sqm": 7400,
        "status": "Good",
    },
    {
        "bridge_id": "DOT-0005",
        "name": "Sterling Heights Overpass (SYNTHETIC)",
        "state": "MI",
        "year_built": 1958,
        "condition_rating": 4,
        "avg_daily_traffic": 38000,
        "deck_area_sqm": 2600,
        "status": "Structurally Deficient",
    },
    {
        "bridge_id": "DOT-0006",
        "name": "Vanguard Canyon Span (SYNTHETIC)",
        "state": "AZ",
        "year_built": 1995,
        "condition_rating": 7,
        "avg_daily_traffic": 15000,
        "deck_area_sqm": 4100,
        "status": "Good",
    },
    {
        "bridge_id": "DOT-0007",
        "name": "Beacon Harbor Drawbridge (SYNTHETIC)",
        "state": "MD",
        "year_built": 1949,
        "condition_rating": 3,
        "avg_daily_traffic": 27000,
        "deck_area_sqm": 1900,
        "status": "Structurally Deficient",
    },
    {
        "bridge_id": "DOT-0008",
        "name": "Aurora Valley Trestle (SYNTHETIC)",
        "state": "CA",
        "year_built": 2012,
        "condition_rating": 9,
        "avg_daily_traffic": 120000,
        "deck_area_sqm": 15600,
        "status": "Good",
    },
    {
        "bridge_id": "DOT-0009",
        "name": "Ironwood Creek Bridge (SYNTHETIC)",
        "state": "TX",
        "year_built": 1977,
        "condition_rating": 5,
        "avg_daily_traffic": 33000,
        "deck_area_sqm": 2950,
        "status": "Fair",
    },
    {
        "bridge_id": "DOT-0010",
        "name": "Summit Pass Arch (SYNTHETIC)",
        "state": "UT",
        "year_built": 1968,
        "condition_rating": 4,
        "avg_daily_traffic": 8000,
        "deck_area_sqm": 3300,
        "status": "Structurally Deficient",
    },
    {
        "bridge_id": "DOT-0011",
        "name": "Keystone Tidal Bridge (SYNTHETIC)",
        "state": "VA",
        "year_built": 1989,
        "condition_rating": 6,
        "avg_daily_traffic": 54000,
        "deck_area_sqm": 6700,
        "status": "Fair",
    },
    {
        "bridge_id": "DOT-0012",
        "name": "Cobalt Ridge Flyover (SYNTHETIC)",
        "state": "PA",
        "year_built": 1955,
        "condition_rating": 2,
        "avg_daily_traffic": 71000,
        "deck_area_sqm": 8200,
        "status": "Structurally Deficient",
    },
]

_NUM_FIELDS = {"year_built", "condition_rating", "avg_daily_traffic", "deck_area_sqm"}


def _apply_filter(rows: list[dict], expr: str) -> list[dict]:
    """Tiny OData-ish $filter: supports `field op value` clauses joined by ' and '.

    Operators: eq, ne, lt, le, gt, ge. Strings in single quotes; numbers bare.
    Unparseable clauses are ignored (best-effort, never 500).
    """
    ops = {
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "lt": lambda a, b: a < b,
        "le": lambda a, b: a <= b,
        "gt": lambda a, b: a > b,
        "ge": lambda a, b: a >= b,
    }
    for clause in re.split(r"\s+and\s+", expr.strip()):
        m = re.match(r"(\w+)\s+(eq|ne|lt|le|gt|ge)\s+(.+)", clause.strip())
        if not m:
            continue
        field, op, raw = m.group(1), m.group(2), m.group(3).strip()
        if raw.startswith("'") and raw.endswith("'"):
            val: object = raw[1:-1]
        else:
            try:
                val = float(raw)
            except ValueError:
                val = raw
        rows = [r for r in rows if field in r and ops[op](r[field], val)]
    return rows


@app.get("/healthz")
def healthz():
    return {"status": "ok", "source": "dot-transportation"}


@app.get("/api/openapi")
def openapi():
    return {
        "openapi": "3.0.1",
        "info": {"title": "DOT Transportation (DAB-style) - REST Endpoint", "version": "1.0"},
        "servers": [{"url": "/api"}],
        "paths": {
            "/Bridge": {
                "get": {
                    "tags": ["Bridge"],
                    "description": "Synthetic National Bridge Inventory records.",
                }
            },
            "/Bridge/bridge_id/{bridge_id}": {
                "get": {"tags": ["Bridge"], "description": "One bridge by id."}
            },
        },
        "x-source": "DOT transportation demo (synthetic stand-in)",
    }


@app.get("/api/Bridge")
def list_bridges(request: Request):
    rows = list(BRIDGES)
    qp = request.query_params
    if "$filter" in qp:
        rows = _apply_filter(rows, qp["$filter"])
    if "$orderby" in qp:
        field, _, direction = qp["$orderby"].partition(" ")
        rows = sorted(
            rows, key=lambda r: r.get(field, 0), reverse=direction.strip().lower() == "desc"
        )
    if "$first" in qp:
        try:
            rows = rows[: int(qp["$first"])]
        except ValueError:
            pass
    if "$select" in qp:
        cols = [c.strip() for c in qp["$select"].split(",")]
        rows = [{k: r[k] for k in cols if k in r} for r in rows]
    return JSONResponse({"value": rows})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
