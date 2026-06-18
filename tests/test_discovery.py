"""Catalog + discovery (PRP Phase 4 AC). Requires the live stack.

* GET /catalog lists the data product;
* GET /catalog/{id} carries owner, classification, request path, and a sample query;
* the OpenAPI contract (public via Kong) documents the entities — schema discovery
  without tribal knowledge.
"""

from __future__ import annotations

import json

import httpx
import pytest
from conftest import CATALOG_URL, KONG_PROXY, requires_stack

pytestmark = [requires_stack, pytest.mark.integration]


def test_catalog_lists_the_product():
    resp = httpx.get(f"{CATALOG_URL}/catalog", timeout=10)
    assert resp.status_code == 200, resp.text
    ids = [p["id"] for p in resp.json()["products"]]
    assert "artemis-supply-risk" in ids


def test_product_detail_has_owner_classification_and_path():
    resp = httpx.get(f"{CATALOG_URL}/catalog/artemis-supply-risk", timeout=10)
    assert resp.status_code == 200, resp.text
    product = resp.json()
    assert product["owner"]
    assert product["request_path"] == "/api/SupplyRisk"
    assert product["openapi_url"].endswith("/api/openapi")
    assert "sample_query" in product
    classification = product["classification"]
    # classify-before-exposure: per-table labels are surfaced from classification.yml
    assert classification["tables"].get("supply_risk")
    assert classification["columns"]["purchase_orders"].get("NETPR") == "Confidential"


def test_openapi_discovery_documents_entities():
    # Discovery contract is public (no token) through the gateway.
    resp = httpx.get(f"{KONG_PROXY}/api/openapi", timeout=10)
    assert resp.status_code == 200, resp.text
    spec_text = json.dumps(resp.json())
    for entity in ("Material", "Vendor", "PurchaseOrder", "SupplyRisk"):
        assert entity in spec_text, f"{entity} should appear in the OpenAPI contract"
