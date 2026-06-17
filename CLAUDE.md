# CLAUDE.md — nasa-api-first-poc

You are the coding agent building this proof-of-concept. **Read `PRP.md` in full
first** — it is the complete, self-contained build spec (mission, success criteria,
architecture, tech stack, repo structure, phased plan, per-file contracts, hard
constraints, Definition of Done). Build exactly what it specifies.

## Mission (one line)

A fully local, `docker compose up` demo of the API-first **zero-move** data-marketplace
pattern, proven on synthetic Artemis SAP-procurement data: Postgres system-of-record →
**Data API Builder** (auto REST/GraphQL) → **Kong OSS gateway** (JWT + rate-limit +
metering) → **catalog** → a **Python client + MCP tool** that answer a real supply-chain
question through the gateway, with **Prometheus/Grafana** observability and a documented
Azure-deployment path.

## How to work

- **Follow the phases in PRP.md §7** (Scaffold → Data/SoR → Auto-API → Identity/Gateway
  → Catalog/Discovery → Consumers → Observability → Docs/Azure → optional UI). Keep each
  phase green (lint + tests + compose smoke) before starting the next.
- **Use TodoWrite** to track the phase tasks. Commit per phase with conventional
  messages (`feat:`, `fix:`, `docs:`, `chore:`).
- **The synthetic data is already provided** at `data/synthetic_data.py`
  (`generate_artemis_procurement(out_dir, seed=42)`) — the seeder calls it; don't
  rewrite it.
- **The program narrative is in `docs/whitepapers/`** — the running code is the proof
  of that narrative; keep them consistent.
- Finish only when every box in PRP.md §13 (Definition of Done) is checked, then write
  `docs/DEMO-SCRIPT.md` a presenter can follow live in ~10 minutes.

## Tech stack (pinned — see PRP §3)

Docker Compose · PostgreSQL 16 · Microsoft Data API Builder · Kong Gateway 3.x OSS
(DB-less) · a minimal local RS256 JWT issuer · Python 3.11 + FastAPI (catalog, seeder,
MCP server) · `mcp` Python SDK · httpx · Prometheus + Grafana · Bicep (Azure reference,
not required to run) · `ruff` + `pytest` + pre-commit + GitHub Actions.

## Hard constraints (non-negotiable — CI checks where possible)

1. **No Microsoft Fabric / OneLake** as a component or recommendation anywhere (not in
   Azure Gov/GCC). A single "explicitly excluded, and why" sentence in docs is fine.
   `tests/test_no_fabric.py` greps the repo.
2. **Zero-move is real, not just claimed.** Postgres and DAB attach only to an
   `internal` Docker network; the ONLY path to data for clients is **through Kong**.
   `tests/test_zero_move.py` proves Postgres/DAB are unreachable from the client network.
3. **Azure pricing is live + dated, never invented.** `tools/azure_pricing.py` hits the
   public Azure Retail Prices API (`https://prices.azure.com/api/retail/prices`, no auth)
   and every figure carries exactly: `Source: Azure Retail Prices API, list price (PAYG),
   <region>, retrieved <YYYY-MM-DD>; excludes EA/MCA/commit discounts.` **No
   staffing/services dollar figures anywhere.**
4. **Synthetic data only.** The `data/README.md` "SYNTHETIC — not real NASA data"
   banner stays; no real-data ingestion paths. ITAR/CUI-safe.
5. **Gateway framed vendor-neutral** in docs — Kong (OSS) is the built path; Azure API
   Management (managed) is the documented Azure equivalent; competitors are not named in
   comparisons.
6. **Open standards** — OData-style REST, OpenAPI, OAuth2/JWT, MCP. No proprietary
   client required to consume the API.
7. **Data platform posture** (for the Azure-deployment doc): the managed platform —
   Azure Databricks with managed Unity Catalog + Databricks SQL + Delta Lake + Delta
   Sharing on ADLS Gen2 — runs in **commercial Azure at FedRAMP High**; the
   managed-UC/Databricks-SQL gap is the **Azure-Government (ITAR/strict-CUI) exception
   only**, not the default. Don't present OSS-UC-on-agency-compute as the primary.

## Coding conventions

- Python: `ruff format` + `ruff check` clean; type hints; small, testable modules;
  fail-safe (services degrade gracefully, never crash on a missing optional dep).
- Config via `.env` (copy from `.env.example`); never commit secrets.
- Every service has a Dockerfile + a healthcheck; `docker-compose.yml` uses
  `depends_on: condition: service_healthy`.
- Keep `README.md` quickstart working from a clean clone on a machine with only Docker.

## Definition of done

See PRP.md §13. In short: `cp .env.example .env && make demo` brings the stack up
healthy and prints the Artemis-3 supply-risk answer sourced through Kong (with a gateway
correlation id); no-token → 401, valid token → 200, over-limit → 429; zero-move proven by
test; catalog + MCP work; Grafana shows per-consumer traffic; `azure_pricing.py` prints
live dated prices; `test_no_fabric.py` passes; all docs present; CI green.
