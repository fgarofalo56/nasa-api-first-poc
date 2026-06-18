"""Live Azure pricing helper for the "what would this cost on Azure" story.

Hard constraint (PRP §9): prices are pulled LIVE from the public Azure Retail Prices
API (no auth) and every figure carries the exact dated source note. Nothing is
hardcoded or invented, and there are NO staffing/services dollar figures anywhere.

Each component below maps to a managed Azure-Gov target service in the deployment path
(APIM <-> Kong, PostgreSQL Flexible Server <-> local Postgres, Container Apps <-> DAB,
Azure Monitor <-> Prometheus/Grafana). The tool degrades gracefully: if a region returns
no PAYG list price for a component, it says so instead of failing.

Usage:
  python tools/azure_pricing.py [--region usgovvirginia] [--currency USD]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys

import httpx

API = "https://prices.azure.com/api/retail/prices"
API_VERSION = "2023-01-01-preview"

# (label, OData $filter fragment) - region + currency are appended at query time.
COMPONENTS = [
    (
        "API Management (gateway <-> Kong)",
        "serviceName eq 'API Management' and priceType eq 'Consumption'",
    ),
    (
        "PostgreSQL Flexible Server (system of record)",
        "serviceName eq 'Azure Database for PostgreSQL' and priceType eq 'Consumption'",
    ),
    (
        "Container Apps (Data API Builder host)",
        "serviceName eq 'Azure Container Apps' and priceType eq 'Consumption'",
    ),
    (
        "Azure Monitor (metrics <-> Prometheus/Grafana)",
        "serviceName eq 'Azure Monitor' and priceType eq 'Consumption'",
    ),
]


def source_note(region: str, retrieved: str) -> str:
    return (
        f"Source: Azure Retail Prices API, list price (PAYG), {region}, "
        f"retrieved {retrieved}; excludes EA/MCA/commit discounts."
    )


def fetch(
    client: httpx.Client, region: str, currency: str, filt: str, limit: int = 3
) -> list[dict]:
    full = f"armRegionName eq '{region}' and {filt}"
    params = {"$filter": full, "currencyCode": currency, "api-version": API_VERSION}
    try:
        resp = client.get(API, params=params, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"  ! query failed ({exc}); skipping", file=sys.stderr)
        return []
    items = [it for it in resp.json().get("Items", []) if it.get("retailPrice", 0) > 0]
    items.sort(key=lambda it: it["retailPrice"])
    return items[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live Azure Retail Prices for the POC's targets")
    parser.add_argument("--region", default=os.environ.get("AZURE_PRICE_REGION", "usgovvirginia"))
    parser.add_argument("--currency", default="USD")
    args = parser.parse_args(argv)

    retrieved = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%d")
    note = source_note(args.region, retrieved)

    print(f"\nAzure managed-target pricing - region '{args.region}', {args.currency}")
    print("(reference for the Azure-Gov deployment path; the POC itself runs on OSS/local)\n")

    any_rows = False
    with httpx.Client() as client:
        for label, filt in COMPONENTS:
            print(f"- {label}")
            rows = fetch(client, args.region, args.currency, filt)
            if not rows:
                print(
                    f"    no PAYG list price returned for '{args.region}' "
                    "(SKU may be unavailable in this region)\n"
                )
                continue
            any_rows = True
            for it in rows:
                price = it["retailPrice"]
                uom = it.get("unitOfMeasure", "")
                meter = it.get("meterName", it.get("skuName", ""))
                print(f"    {price:>14,.6f} {args.currency} / {uom:18}  {meter}")
            print()

    print(note)
    if not any_rows:
        print(
            "\n(No priced SKUs returned - the Government region may not expose these meters; "
            "re-run with --region eastus to see the commercial-Azure list prices.)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
