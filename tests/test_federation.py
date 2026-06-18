"""Multi-source federation + control-plane (registry) — requires the live stack.

Proves the "add a source through the gateway, live" path: register a second source via
the registry (which hot-reloads Kong), confirm it is governed + queryable through the
gateway and listed in the catalog, then remove it (hot-reload) and confirm it is gone.
"""

from __future__ import annotations

import httpx
import pytest
from conftest import CATALOG_URL, REGISTRY_URL, gateway_get, get_token, requires_stack

pytestmark = [requires_stack, pytest.mark.integration]

TEST_SOURCE = {
    "id": "test-fed",
    "title": "Test Federation Source",
    "upstream_url": "http://transportation:8200",
    "base_path": "/testfed",
    "owner": "pytest",
    "domain": "Test",
    "classification_label": "Routine",
    "require_jwt": True,
    "sample_path": "/testfed/api/Bridge?$first=3",
}


@pytest.fixture
def registered_source():
    # ensure clean, then register; always clean up
    httpx.delete(f"{REGISTRY_URL}/sources/{TEST_SOURCE['id']}", timeout=20)
    resp = httpx.post(f"{REGISTRY_URL}/sources", json=TEST_SOURCE, timeout=30)
    resp.raise_for_status()
    yield TEST_SOURCE
    httpx.delete(f"{REGISTRY_URL}/sources/{TEST_SOURCE['id']}", timeout=20)


def test_registered_source_is_governed_and_queryable(registered_source):
    # no token -> 401 at the edge (the new route inherits gateway governance)
    assert gateway_get("/testfed/api/Bridge").status_code == 401
    # with a token -> 200 + rows through Kong
    resp = gateway_get("/testfed/api/Bridge?$first=3", token=get_token("analyst"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["value"], "the federated source should return rows through Kong"


def test_registered_source_appears_in_catalog(registered_source):
    products = httpx.get(f"{CATALOG_URL}/catalog", timeout=10).json()["products"]
    assert any(p["id"] == "test-fed" for p in products)


def test_removed_source_is_gone():
    httpx.delete(f"{REGISTRY_URL}/sources/{TEST_SOURCE['id']}", timeout=20)
    # the route should no longer exist (Kong hot-reloaded without it)
    resp = gateway_get("/testfed/api/Bridge?$first=1", token=get_token("analyst"))
    assert resp.status_code in (404, 401), f"expected route gone, got {resp.status_code}"
