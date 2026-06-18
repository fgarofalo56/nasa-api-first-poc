"""Offline unit tests for the registry's Kong route builder.

These run without the stack (no `requires_stack`): they import the registry module and
assert that a wizard-registered source gets the SAME governance plugin set as the
built-in Artemis route in `services/gateway/kong.yml` — so a federated source is never
weaker than the first-party one. (Regression guard for the OWASP-guard drift.)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# The registry app imports FastAPI; skip cleanly if web deps aren't in this environment.
pytest.importorskip("fastapi")
pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_registry():
    spec = importlib.util.spec_from_file_location(
        "registry_app", REPO_ROOT / "services" / "registry" / "app.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REG = _load_registry()


def _plugin_names(src: dict) -> set[str]:
    route = REG._kong_route_for(src)
    return {p["name"] for p in route["plugins"]}


def test_jwt_source_gets_full_governance_set():
    names = _plugin_names(
        {"id": "x", "upstream_url": "http://u:1", "base_path": "/x", "require_jwt": True}
    )
    expected = {
        "correlation-id",
        "jwt",
        "rate-limiting",
        "cors",
        "pre-function",
        "request-transformer",
    }
    assert expected <= names, f"missing governance plugins: {expected - names}"


def test_safety_controls_present_even_without_jwt():
    # A public (no-JWT) source still gets the OWASP guard + identity-header strip.
    names = _plugin_names(
        {"id": "y", "upstream_url": "http://u:1", "base_path": "/y", "require_jwt": False}
    )
    assert {"pre-function", "request-transformer"} <= names


def test_request_transformer_strips_identity_spoofing_headers():
    route = REG._kong_route_for(
        {"id": "z", "upstream_url": "http://u:1", "base_path": "/z", "require_jwt": True}
    )
    rt = next(p for p in route["plugins"] if p["name"] == "request-transformer")
    removed = rt["config"]["remove"]["headers"]
    assert "X-MS-CLIENT-PRINCIPAL" in removed
    assert "X-MS-API-ROLE" in removed


def test_owasp_guard_blocks_over_broad_extraction():
    route = REG._kong_route_for(
        {"id": "w", "upstream_url": "http://u:1", "base_path": "/w", "require_jwt": True}
    )
    pre = next(p for p in route["plugins"] if p["name"] == "pre-function")
    access_lua = " ".join(pre["config"]["access"])
    assert "$first" in access_lua and "200" in access_lua
