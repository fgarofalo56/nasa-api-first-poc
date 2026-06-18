"""Shared pytest fixtures + helpers.

The integration tests (zero-move / gateway-auth / discovery / supply-risk) need the
docker-compose stack running. When it is not reachable (e.g. the offline lint+unit CI
job) they SKIP rather than fail, so `make test` is green on a clean checkout and the
compose-smoke CI job exercises the live path.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Endpoints (host-side ports; override via env to match a remote/CI stack).
KONG_PROXY = os.environ.get("KONG_PROXY_URL", "http://localhost:8000")
KONG_ADMIN = os.environ.get("KONG_ADMIN_URL", "http://localhost:8001")
IDENTITY_URL = os.environ.get("IDENTITY_URL", "http://localhost:8081")
CATALOG_URL = os.environ.get("CATALOG_URL", "http://localhost:8080")

# Internal hostnames (only resolvable/reachable from inside Docker networks).
POSTGRES_HOST = os.environ.get("POSTGRES_HOST_TEST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))


def stack_up() -> bool:
    """True when *our* Kong gateway answers on the admin status endpoint.

    Validates the JSON shape so an unrelated local service on the same port does not
    produce a false positive.
    """
    try:
        resp = httpx.get(f"{KONG_ADMIN}/status", timeout=1.5)
        body = resp.json()
        return resp.status_code == 200 and "memory" in body
    except Exception:
        return False


requires_stack = pytest.mark.skipif(
    not stack_up(),
    reason="docker-compose stack not reachable (start it with `make up`)",
)


def get_token(consumer: str = "analyst") -> str:
    """Fetch an RS256 bearer token from the local identity issuer."""
    resp = httpx.post(f"{IDENTITY_URL}/token", json={"consumer": consumer}, timeout=10)
    resp.raise_for_status()
    return resp.json()["access_token"]


def gateway_get(path: str, token: str | None = None, **kwargs) -> httpx.Response:
    """GET through the Kong gateway, optionally with a bearer token."""
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.get(f"{KONG_PROXY}{path}", headers=headers, timeout=15, **kwargs)


def tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """True if a TCP connection to host:port can be established."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
