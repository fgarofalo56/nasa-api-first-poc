"""Gateway auth + governance (PRP Phase 3 AC). Requires the live stack.

* no token / invalid token  -> 401 at the edge (request never reaches DAB)
* valid token               -> 200, with an X-Correlation-ID echoed
* over the rate cap         -> 429 with Retry-After
* over-broad extraction     -> 400 (the OWASP API4 pre-function guard)
"""

from __future__ import annotations

import collections

import httpx
import pytest
from conftest import KONG_PROXY, gateway_get, get_token, requires_stack

pytestmark = [requires_stack, pytest.mark.integration]

API = "/api/SupplyRisk?$first=1"


def test_no_token_is_rejected_at_edge():
    assert gateway_get(API).status_code == 401


def test_invalid_token_is_rejected():
    resp = gateway_get(API, headers={"Authorization": "Bearer not.a.valid.jwt"})
    assert resp.status_code == 401


def test_valid_token_passes_with_correlation_id():
    resp = gateway_get(API, token=get_token("analyst"))
    assert resp.status_code == 200, resp.text
    assert "value" in resp.json()
    assert resp.headers.get("X-Correlation-ID"), "gateway correlation id should be echoed"


def test_over_broad_query_is_blocked():
    # OWASP API4:2023 — $first beyond the cap is rejected before reaching DAB.
    resp = gateway_get("/api/Material?$first=99999", token=get_token("analyst"))
    assert resp.status_code == 400, resp.text


def test_over_rate_limit_returns_429_with_retry_after():
    # Burst as artemis-agent (separate consumer) so other tests' analyst quota is intact.
    token = get_token("artemis-agent")
    headers = {"Authorization": f"Bearer {token}"}
    codes: collections.Counter = collections.Counter()
    retry_after = None
    with httpx.Client(base_url=KONG_PROXY, timeout=15) as client:
        for _ in range(90):
            resp = client.get("/api/Material?$first=1", headers=headers)
            codes[resp.status_code] += 1
            if resp.status_code == 429 and retry_after is None:
                retry_after = resp.headers.get("Retry-After")
    assert codes[429] > 0, f"expected some 429s over the cap, got {dict(codes)}"
    assert retry_after is not None, "429 should carry Retry-After"
