"""Governed consumer CLI — answers the Artemis supply-risk question through Kong.

Flow (never touches the database directly):
  1. obtain an RS256 bearer token from the local identity issuer (stands in for Entra),
  2. call the SupplyRisk data product THROUGH the Kong gateway with an OData filter,
  3. enrich each high-risk part with its supplier (PurchaseOrder -> Vendor, also via Kong),
  4. print the ranked answer + the gateway correlation id (proof it went through Kong).

Usage:
  python client/query_supply_risk.py --program Artemis-3 --min-delay 30
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

IDENTITY_URL = os.environ.get("IDENTITY_URL", "http://localhost:8081").rstrip("/")
KONG_URL = os.environ.get("KONG_URL", "http://localhost:8000").rstrip("/")
CORR_HEADER = "X-Correlation-ID"


def get_token(client: httpx.Client, consumer: str) -> str:
    resp = client.post(f"{IDENTITY_URL}/token", json={"consumer": consumer}, timeout=10)
    resp.raise_for_status()
    return resp.json()["access_token"]


def build_filter(program: str, min_delay: int, criticality: str | None, sole_source: bool) -> str:
    clauses = [f"program eq '{program}'", f"avg_delay_days gt {min_delay}"]
    if criticality:
        clauses.append(f"criticality eq '{criticality}'")
    if sole_source:
        clauses.append("sole_source eq true")
    return " and ".join(clauses)


def query_supply_risk(
    client: httpx.Client,
    token: str,
    program: str,
    min_delay: int,
    criticality: str | None,
    sole_source: bool,
) -> tuple[list[dict], str | None]:
    headers = {"Authorization": f"Bearer {token}"}
    # Build the query string into the URL so httpx encodes spaces as %20 (DAB's OData
    # parser rejects the '+' encoding that a params= dict would produce).
    flt = build_filter(program, min_delay, criticality, sole_source)
    url = f"{KONG_URL}/api/SupplyRisk?$filter={flt}&$orderby=risk_score desc"
    resp = client.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json().get("value", []), resp.headers.get(CORR_HEADER)


def supplier_for(client: httpx.Client, token: str, matnr: str) -> str:
    """Best-effort: find a supplier for a material via PurchaseOrder -> Vendor (through Kong)."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        po = client.get(
            f"{KONG_URL}/api/PurchaseOrder?$filter=matnr eq '{matnr}'&$first=1&$select=lifnr",
            headers=headers,
            timeout=15,
        )
        po.raise_for_status()
        rows = po.json().get("value", [])
        if not rows:
            return "(no PO found)"
        lifnr = rows[0]["lifnr"]
        ven = client.get(
            f"{KONG_URL}/api/Vendor?$filter=lifnr eq {lifnr}&$select=name1,cage_code",
            headers=headers,
            timeout=15,
        )
        ven.raise_for_status()
        vrows = ven.json().get("value", [])
        if not vrows:
            return f"LIFNR {lifnr}"
        return f"{vrows[0]['name1']} (CAGE {vrows[0].get('cage_code', '?')})"
    except httpx.HTTPError:
        return "(supplier lookup unavailable)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query Artemis supply risk through the gateway")
    parser.add_argument("--program", default="Artemis-3")
    parser.add_argument("--min-delay", type=int, default=30)
    parser.add_argument("--consumer", default="analyst", help="analyst | artemis-agent")
    parser.add_argument("--criticality", default="Critical", help="set empty to include all")
    parser.add_argument(
        "--include-non-sole-source",
        action="store_true",
        help="include materials that are not sole-source",
    )
    parser.add_argument("--no-suppliers", action="store_true", help="skip supplier enrichment")
    args = parser.parse_args(argv)

    criticality = args.criticality or None
    sole_source = not args.include_non_sole_source

    with httpx.Client() as client:
        token = get_token(client, args.consumer)
        rows, corr = query_supply_risk(
            client, token, args.program, args.min_delay, criticality, sole_source
        )
        suppliers = {}
        if not args.no_suppliers:
            for r in rows:
                suppliers[r["matnr"]] = supplier_for(client, token, r["matnr"])

    crit_label = criticality or "any-criticality"
    ss_label = "sole-source" if sole_source else "any-sourcing"
    print(
        f"\nQ: Which {crit_label}, {ss_label} materials on {args.program} "
        f"have an average delay > {args.min_delay} days?\n"
    )
    if not rows:
        print("  (no materials matched — try --min-delay 0 or --include-non-sole-source)")
    else:
        print(f"  {'TIER':5} {'RISK':>4} {'AVG_DLY':>7}  {'MATERIAL':28} SUPPLIER")
        print(f"  {'-' * 5} {'-' * 4} {'-' * 7}  {'-' * 28} {'-' * 30}")
        for r in rows:
            sup = suppliers.get(r["matnr"], "") if not args.no_suppliers else ""
            print(
                f"  {r['risk_tier']:5} {r['risk_score']:>4} {float(r['avg_delay_days']):>7.1f}  "
                f"{r['maktx'][:28]:28} {sup}"
            )
    print(
        f"\n  consumer={args.consumer}  results={len(rows)}  gateway correlation-id={corr}"
        "\n  Data never left Postgres -- every row was brokered through Kong "
        "(JWT-authenticated, rate-limited, metered).\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
