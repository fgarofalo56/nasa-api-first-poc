"""Marketplace catalog (the APIM dev-portal / API Center analogue).

Publishes the data product so it is discoverable without tribal knowledge: title,
owner, classification (merged from data/classification.yml — classify-before-exposure),
the request path, the OpenAPI contract URL (public, via Kong), and a ready-to-run
sample query. Reads catalog.json + classification.yml at startup.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException

APP_DIR = Path(__file__).resolve().parent
CATALOG_JSON = Path(os.environ.get("CATALOG_JSON", APP_DIR / "catalog.json"))
CLASSIFICATION_YML = Path(os.environ.get("CLASSIFICATION_YML", APP_DIR / "classification.yml"))
PORT = int(os.environ.get("CATALOG_PORT", "8080"))
# Public base URL clients use to reach Kong (for the OpenAPI + request path links).
KONG_PUBLIC_URL = os.environ.get("KONG_PUBLIC_URL", "http://localhost:8000").rstrip("/")

app = FastAPI(title="Artemis Data Marketplace Catalog", version="0.1.0")


def _load_catalog() -> dict:
    return json.loads(CATALOG_JSON.read_text(encoding="utf-8"))


def _load_classification() -> dict:
    if not CLASSIFICATION_YML.exists():
        return {}
    return yaml.safe_load(CLASSIFICATION_YML.read_text(encoding="utf-8")) or {}


def _classification_summary() -> dict:
    """Surface the per-table/column sensitivity labels (Purview-style)."""
    manifest = _load_classification()
    tables = manifest.get("tables") or {}
    return {
        "dataset": manifest.get("dataset"),
        "default_label": manifest.get("default_label"),
        "source": "data/classification.yml (applied to the SoR as column comments at seed)",
        "tables": {t: spec.get("label") for t, spec in tables.items()},
        "columns": {t: (spec.get("columns") or {}) for t, spec in tables.items()},
    }


def _enrich(product: dict) -> dict:
    """Add absolute, gateway-relative URLs + the classification block."""
    p = dict(product)
    p["openapi_url"] = f"{KONG_PUBLIC_URL}{product['openapi_path']}"
    p["request_url"] = f"{KONG_PUBLIC_URL}{product['request_path']}"
    if "sample_query" in p:
        sq = dict(p["sample_query"])
        sq["url"] = f"{KONG_PUBLIC_URL}{sq['path']}?{sq['odata']}"
        p["sample_query"] = sq
    p["classification"] = _classification_summary()
    return p


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/catalog")
def list_catalog():
    catalog = _load_catalog()
    products = [
        {
            "id": p["id"],
            "title": p["title"],
            "owner": p["owner"],
            "domain": p["domain"],
            "request_path": p["request_path"],
            "openapi_url": f"{KONG_PUBLIC_URL}{p['openapi_path']}",
            "classification_dataset": (_load_classification() or {}).get("dataset"),
            "detail": f"/catalog/{p['id']}",
        }
        for p in catalog.get("products", [])
    ]
    return {"marketplace": catalog.get("marketplace"), "count": len(products), "products": products}


@app.get("/catalog/{product_id}")
def get_product(product_id: str):
    catalog = _load_catalog()
    for product in catalog.get("products", []):
        if product["id"] == product_id:
            return _enrich(product)
    raise HTTPException(status_code=404, detail=f"unknown product '{product_id}'")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
