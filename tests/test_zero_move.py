"""Zero-move proof (PRP §9 hard constraint). Requires the live stack + docker.

The system-of-record (Postgres) and the auto-API (DAB) live ONLY on the `internal`
network and publish no host ports. We prove the data has exactly one path — through
Kong — by showing:

  * a container on the `edge` network (where clients live) CANNOT reach postgres:5432
    or dab:5000 (name does not resolve / connection refused), but CAN reach kong:8000;
  * compose publishes no host port for postgres or dab; and
  * the same query still succeeds through the Kong proxy.
"""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest
from conftest import REPO_ROOT, gateway_get, get_token, requires_stack

pytestmark = [requires_stack, pytest.mark.integration]

_DOCKER = shutil.which("docker")
needs_docker = pytest.mark.skipif(_DOCKER is None, reason="docker CLI not available")


def _edge_network() -> str | None:
    out = subprocess.run(
        ["docker", "network", "ls", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
    )
    for name in out.stdout.split():
        if name.endswith("_edge"):
            return name
    return None


def _connect_from_edge(host: str, port: int) -> bool:
    """True if a throwaway container on the edge network can TCP-connect to host:port."""
    net = _edge_network()
    assert net, "edge network not found; is the stack up?"
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            net,
            "busybox",
            "sh",
            "-c",
            f"nc -z -w3 {host} {port}",
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _published(service: str, port: int) -> bool:
    # `docker compose port` prints a real binding ("0.0.0.0:8081") when published, and
    # ":0" / "invalid IP:0" / an error when it is not. Match only a real IPv4:port.
    result = subprocess.run(
        ["docker", "compose", "port", service, str(port)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3}):(\d+)", result.stdout or "")
    return bool(match) and int(match.group(2)) != 0


@needs_docker
def test_postgres_unreachable_from_edge_network():
    assert not _connect_from_edge("postgres", 5432), "Postgres must not be reachable by clients"


@needs_docker
def test_dab_unreachable_from_edge_network():
    assert not _connect_from_edge("dab", 5000), "DAB must not be reachable by clients"


@needs_docker
def test_kong_is_reachable_from_edge_network():
    assert _connect_from_edge("kong", 8000), "Kong is the one path and must be reachable"


@needs_docker
def test_postgres_and_dab_publish_no_host_ports():
    assert not _published("postgres", 5432), "Postgres must not publish a host port"
    assert not _published("dab", 5000), "DAB must not publish a host port"


def test_data_still_answers_through_the_gateway():
    resp = gateway_get("/api/SupplyRisk?$first=1", token=get_token("analyst"))
    assert resp.status_code == 200, resp.text
    assert resp.json()["value"], "the gateway is the working path to the data"
