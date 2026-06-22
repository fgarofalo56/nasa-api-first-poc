"""Rebuild docs/architecture.excalidraw — the zero-move, multi-source reference
architecture — from a small declarative spec, using the Excalidraw diagram-compiler.

The committed **docs/architecture.png** is the rendered image used in the docs; it is
exported from **docs/architecture.excalidraw** (the editable source of truth). To edit
the diagram, either open the `.excalidraw` file at https://excalidraw.com and re-export
PNG, or change the spec below and re-run this script to regenerate the scene.

This script depends on the local Excalidraw diagram compiler under
``~/.claude/skills/excalidraw``. If that tooling isn't present, it prints a note and
exits 0 (fail-safe) — the committed ``.excalidraw`` + ``.png`` stay authoritative.

Run: python scripts/gen-architecture-diagram.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "docs" / "architecture.excalidraw"
SKILL = Path.home() / ".claude" / "skills" / "excalidraw"


def build_spec(libs: Path) -> dict:
    kong = str(libs / "azure" / "logos.excalidrawlib")
    fabric = str(libs / "azure" / "microsoft-fabric-architecture-icons.excalidrawlib")
    general = str(libs / "azure" / "azure-general.excalidrawlib")
    return {
        "title": "NASA API-first · zero-move · multi-source data marketplace",
        "subtitle": "Data stays in its source — every call is brokered, authenticated, "
        "rate-limited and metered by the gateway (local OSS analogue).",
        "theme": "dark",
        "services": {
            "registry": {
                "title": "Registry",
                "desc": "Control-plane\nonboarding wizard",
                "icon": "Azure Policy",
                "kind": "security",
                "layer": 0,
                "lane": 1,
            },
            "consumers": {
                "title": "Consumers",
                "desc": "Python CLI · MCP agent\nNASA-themed UI",
                "icon": "User",
                "icon_lib": fabric,
                "kind": "compute",
                "layer": 0,
                "lane": 2,
            },
            "catalog": {
                "title": "Catalog",
                "desc": "Products · owner\nclassification",
                "icon": "Microsoft Purview",
                "kind": "data",
                "layer": 0,
                "lane": 4,
            },
            "identity": {
                "title": "Identity issuer",
                "desc": "RS256 JWT + JWKS",
                "icon": "Key Vault",
                "kind": "security",
                "layer": 1,
                "lane": 0,
            },
            "kong": {
                "title": "Kong Gateway (OSS)",
                "desc": "JWT · rate-limit · meter\ncorrelation-id · OWASP",
                "icon": "Kong",
                "icon_lib": kong,
                "kind": "network",
                "layer": 1,
                "lane": 2,
            },
            "dot": {
                "title": "DOT Transportation API",
                "desc": "2nd source\nadded via wizard",
                "icon": "App Service",
                "kind": "api",
                "layer": 2,
                "lane": 1,
            },
            "dab": {
                "title": "Data API Builder",
                "desc": "auto REST · GraphQL\nOpenAPI",
                "icon": "Function App",
                "kind": "compute",
                "layer": 2,
                "lane": 3,
            },
            "prometheus": {
                "title": "Prometheus + Grafana",
                "desc": "per-consumer metrics",
                "icon": "Dashboard",
                "icon_lib": general,
                "kind": "compute",
                "layer": 2,
                "lane": 4,
            },
            "postgres": {
                "title": "PostgreSQL 16",
                "desc": "Artemis SAP procurement\n(system of record)",
                "icon": "Postgres",
                "kind": "storage",
                "layer": 3,
                "lane": 3,
                "shape": "ellipse",
            },
        },
        "edges": [
            {"from": "consumers", "to": "kong", "label": "bearer token · REST"},
            {
                "from": "identity",
                "to": "kong",
                "label": "JWKS · RS256",
                "style": "dashed",
                "color": "#fb7185",
            },
            {
                "from": "registry",
                "to": "kong",
                "label": "hot-reload /config",
                "style": "dashed",
                "color": "#a78bfa",
            },
            {"from": "kong", "to": "dab", "label": "REST / OData"},
            {"from": "kong", "to": "dot", "label": "federated route"},
            {"from": "dab", "to": "postgres", "label": "SQL (stays put)"},
            {"from": "kong", "to": "catalog", "label": "publishes contract"},
            {"from": "kong", "to": "prometheus", "label": "scrape /metrics"},
        ],
        "notes": [
            {
                "text": "Zero-move\n\nPostgres + DAB sit on an\ninternal Docker network with\n"
                "no host ports. The only path\nto data is through Kong.",
                "near": "postgres",
                "side": "right",
            },
            {
                "text": "Federation\n\nDOT is a 2nd source added\nlive via the registry\n"
                "control-plane — no restart.",
                "near": "dot",
                "side": "left",
            },
        ],
    }


def main() -> int:
    compiler = SKILL / "scripts" / "diagram_compiler.py"
    if not compiler.exists():
        print(
            f"Excalidraw diagram compiler not found at {compiler}.\n"
            "The committed docs/architecture.excalidraw and docs/architecture.png remain "
            "the source of truth; skipping regeneration."
        )
        return 0

    sys.path.insert(0, str(SKILL / "scripts"))
    from diagram_compiler import compile_diagram, print_violations, validate_layout

    spec = build_spec(SKILL / "libraries")
    scene = compile_diagram(spec)
    print_violations(validate_layout(scene))
    OUT.write_text(json.dumps(scene), encoding="utf-8")
    print(f"wrote {OUT} ({len(scene.get('elements', []))} elements)")
    print("Export docs/architecture.png from this scene in Excalidraw (Export image → PNG).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
