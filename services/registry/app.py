"""Source registry / control-plane — "add a data source through the gateway, live."

Powers the onboarding wizard. Registering a source:
  1. validates the request,
  2. loads the base Kong declarative config (rendered by identity into /shared/kong.yml,
     so the RSA keys + consumers + the Artemis service are preserved),
  3. merges a Kong service + route (+ governance plugins) for each registered source,
  4. hot-reloads Kong via the admin `/config` endpoint (DB-less), and
  5. persists the source list so the catalog can list it and it survives restarts.

This is the local analogue of registering an API in Azure API Management / API Center.
No source is modified — only the gateway learns a new upstream.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import httpx
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(levelname)s registry %(message)s")
log = logging.getLogger("registry")

PORT = int(os.environ.get("REGISTRY_PORT", "8095"))
KONG_ADMIN = os.environ.get("KONG_ADMIN_INTERNAL_URL", "http://kong:8001").rstrip("/")
# Read the base (identity-rendered), write the merged effective config Kong loads — so
# registry-added sources survive a Kong restart, and a delete rebuilds cleanly from base.
BASE_KONG = Path(os.environ.get("KONG_BASE", "/shared/kong.base.yml"))
KONG_RENDERED = Path(os.environ.get("KONG_RENDERED", "/shared/kong.yml"))
SOURCES_FILE = Path(os.environ.get("SOURCES_FILE", "/shared/sources.json"))
RATE_LIMIT = os.environ.get("RATE_LIMIT_PER_MINUTE", "60")
# Pre-registered sources (JSON array) seeded on first start when the store is empty — used
# in Azure so DOT is present-by-default yet removable (and re-addable via the wizard).
SEED_SOURCES_JSON = os.environ.get("SEED_SOURCES_JSON", "")

app = FastAPI(title="Artemis Marketplace — Source Registry", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SourceSpec(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,40}$")
    title: str
    upstream_url: str
    base_path: str = Field(description="Gateway path, e.g. /dot/api")
    owner: str = "Unspecified"
    domain: str = "Unspecified"
    classification_label: str = "Routine"
    require_jwt: bool = True
    sample_path: str | None = None


def _load_sources() -> list[dict]:
    if SOURCES_FILE.exists():
        try:
            return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def _save_sources(sources: list[dict]) -> None:
    SOURCES_FILE.write_text(json.dumps(sources, indent=2), encoding="utf-8")


def _kong_route_for(src: dict) -> dict:
    plugins = [
        {
            "name": "correlation-id",
            "config": {
                "header_name": "X-Correlation-ID",
                "generator": "uuid#counter",
                "echo_downstream": True,
            },
        }
    ]
    if src.get("require_jwt", True):
        plugins.append(
            {
                "name": "jwt",
                "config": {
                    "key_claim_name": "client_id",
                    "run_on_preflight": False,
                    "claims_to_verify": ["exp"],
                },
            }
        )
        plugins.append(
            {
                "name": "rate-limiting",
                "config": {
                    "minute": int(RATE_LIMIT),
                    "policy": "local",
                    "limit_by": "consumer",
                    "fault_tolerant": True,
                },
            }
        )
    plugins.append(
        {
            "name": "cors",
            "config": {
                "origins": ["*"],
                "methods": ["GET", "OPTIONS"],
                "headers": ["Authorization", "Content-Type"],
                "exposed_headers": ["X-Correlation-ID"],
                "credentials": False,
                "preflight_continue": False,
            },
        }
    )
    # Parity with the built-in Artemis route (services/gateway/kong.yml): every governed
    # source gets the SAME safety controls, so a wizard-added source is not weaker.
    #   pre-function       — OWASP API4 guard: reject over-broad extraction ($first > 200)
    #   request-transformer — strip client-supplied identity headers so the upstream can't
    #                         be tricked into a privileged role (keeps any field redaction real)
    plugins.append(
        {
            "name": "pre-function",
            "config": {
                "access": [
                    "local args = kong.request.get_query()\n"
                    'local first = args["$first"]\n'
                    "if first and tonumber(first) and tonumber(first) > 200 then\n"
                    "  return kong.response.exit(400, { message = "
                    '"Over-broad query blocked (OWASP API4): $first exceeds 200", max_first = 200 })\n'
                    "end"
                ]
            },
        }
    )
    plugins.append(
        {
            "name": "request-transformer",
            "config": {
                "remove": {
                    "headers": [
                        "X-MS-CLIENT-PRINCIPAL",
                        "X-MS-CLIENT-PRINCIPAL-ID",
                        "X-MS-CLIENT-PRINCIPAL-NAME",
                        "X-MS-CLIENT-PRINCIPAL-IDP",
                        "X-MS-API-ROLE",
                    ]
                }
            },
        }
    )
    return {
        "name": f"src-{src['id']}",
        "url": src["upstream_url"],
        # strip_path: the gateway prefix (e.g. /dot) is removed so the upstream receives
        # its own native path (e.g. /api/Bridge).
        "routes": [{"name": f"route-{src['id']}", "paths": [src["base_path"]], "strip_path": True}],
        "plugins": plugins,
    }


def _build_merged_config(sources: list[dict]) -> dict:
    if not BASE_KONG.exists():
        raise HTTPException(503, f"base Kong config {BASE_KONG} not found yet")
    config = yaml.safe_load(BASE_KONG.read_text(encoding="utf-8"))
    config.setdefault("services", [])
    existing = {s.get("name") for s in config["services"]}
    for src in sources:
        svc = _kong_route_for(src)
        if svc["name"] not in existing:
            config["services"].append(svc)
    return config


def _reload_kong(config: dict) -> None:
    # DB-less hot reload: POST the full declarative config to the admin /config endpoint.
    resp = httpx.post(
        f"{KONG_ADMIN}/config",
        params={"check_hash": "1"},
        headers={"Content-Type": "application/json"},
        content=json.dumps(config),
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(502, f"Kong reload failed: {resp.status_code} {resp.text[:400]}")


def _apply(sources: list[dict]) -> None:
    config = _build_merged_config(sources)
    _reload_kong(config)
    # Persist the merged config to the file Kong loads, so a Kong restart keeps the
    # registered sources (no dependency on the registry restarting too).
    try:
        KONG_RENDERED.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    except OSError as exc:
        log.warning("could not persist merged config to %s: %s", KONG_RENDERED, exc)


def _try_apply(sources: list[dict]) -> bool:
    """Best-effort hot-reload. In Azure there is no shared base config or reachable Kong
    admin, so this no-ops gracefully — the source list still persists and the catalog
    (which reads the registry) reflects it; the gateway route is pre-baked there."""
    try:
        _apply(sources)
        return True
    except Exception as exc:  # noqa: BLE001 — degrade gracefully
        log.info("Kong hot-reload skipped/failed (expected in Azure): %s", str(exc)[:120])
        return False


@app.on_event("startup")
def _startup():
    try:
        sources = _load_sources()
        if not sources and SEED_SOURCES_JSON:
            try:
                seed = json.loads(SEED_SOURCES_JSON)
                if isinstance(seed, list) and seed:
                    _save_sources(seed)
                    sources = seed
                    log.info("seeded %s pre-registered source(s)", len(seed))
            except json.JSONDecodeError:
                log.warning("SEED_SOURCES_JSON is not valid JSON; ignoring")
        _try_apply(sources)
        log.info("registry ready with %s source(s)", len(sources))
    except Exception as exc:  # noqa: BLE001 — degrade gracefully on boot
        log.warning("startup issue: %s", exc)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/sources")
def list_sources():
    return {"sources": _load_sources()}


@app.post("/sources")
def add_source(spec: SourceSpec):
    sources = _load_sources()
    if any(s["id"] == spec.id for s in sources):
        raise HTTPException(409, f"source '{spec.id}' already registered")
    src = spec.model_dump()
    sources.append(src)
    _save_sources(sources)  # persist first — the catalog reads the registry as truth
    reloaded = _try_apply(sources)  # best-effort hot-reload (no-op in Azure; route pre-baked)
    log.info("registered source %s -> %s at %s", spec.id, spec.upstream_url, spec.base_path)
    return {"status": "registered", "source": src, "gateway_path": spec.base_path, "gateway_reloaded": reloaded}


@app.delete("/sources/{source_id}")
def remove_source(source_id: str):
    sources = _load_sources()
    remaining = [s for s in sources if s["id"] != source_id]
    if len(remaining) == len(sources):
        raise HTTPException(404, f"source '{source_id}' not found")
    _save_sources(remaining)  # persist first; reload is best-effort
    reloaded = _try_apply(remaining)
    return {"status": "removed", "id": source_id, "gateway_reloaded": reloaded}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
