# nasa-api-first-poc

> **One platform for data, APIs, and code — Microsoft as the secure interoperability
> layer, not "the one AI."** A fully local, `docker compose up` proof-of-concept of
> the API-first, **zero-move** data-marketplace pattern, proven on a synthetic
> **Artemis supply-chain (SAP procurement)** dataset.

This repo is the runnable evidence behind the Microsoft → NASA OCIO API-first
white-paper set: mission data stays in its system of record, an open-source gateway
governs an auto-generated API in front of it, the data product is discoverable in a
catalog, and an agent answers a real supply-chain question **through the gateway** —
with a documented, one-swap path to the Azure-Government managed equivalents.

> **Status: scaffold + build spec.** The services are not implemented yet. This repo
> contains everything a coding agent needs to build them: the complete build spec
> (`PRP.md`), the synthetic data generator, the program narrative (`docs/whitepapers/`),
> the folder structure, and the project rules (`CLAUDE.md`). See **"Start the build"**
> below.

---

## What it demonstrates (once built)

1. **Zero data movement** — the system-of-record data never leaves its database; the
   gateway brokers every call.
2. **Auto-generated API over the system of record** — REST + GraphQL + OpenAPI
   without hand-writing an API (the Microsoft Data API Builder pattern).
3. **A governed gateway in front** — an OSS gateway (Kong) that authenticates
   (JWT/OAuth2), rate-limits, and meters per-consumer — the Azure-API-Management
   pattern in its open-source analogue.
4. **A discoverable catalog** — the API + its OpenAPI contract, owner, classification,
   and request path, findable without tribal knowledge.
5. **A consumer answers a real question through the gateway** — "which Critical,
   sole-source materials on Artemis-3 are slipping > 30 days?" — via a Python client
   **and** an MCP tool an agent can call.
6. **Observability** — per-consumer call/latency metrics on a Grafana dashboard.

## Architecture at a glance (Azure → local mapping)

The POC builds the local/open analogue of each Azure-Government target service, so
the same architecture deploys to Azure later by swapping the gateway, catalog, and
identity for their managed equivalents. Full table in `PRP.md` §2 and
`docs/ARCHITECTURE.md`.

| Azure target | POC local analogue |
|---|---|
| System of record (SAP procurement) | PostgreSQL (synthetic SAP-shaped tables) |
| Expose data as an API (no code) | **Microsoft Data API Builder** over Postgres |
| Azure API Management | **Kong Gateway OSS** (DB-less) |
| Microsoft Entra ID | local OIDC/JWT issuer |
| Enterprise API catalog | FastAPI catalog service |
| Microsoft Purview (classify) | `data/classification.yml` applied at seed |
| Foundry/Copilot agent (MCP) | local MCP server + Python client |
| Azure Monitor / App Insights | Prometheus + Grafana |

> **Data platform note:** for the federal customer this POC models, the managed data
> platform (Azure Databricks with managed Unity Catalog + Databricks SQL + Delta
> Lake + Delta Sharing on ADLS Gen2) runs in **commercial Azure at FedRAMP High** —
> the open-source-rooted formats keep it divestable. Microsoft Fabric / OneLake are
> excluded (not in Azure Gov/GCC). Details in `docs/AZURE-DEPLOYMENT.md`.

## Quickstart (after the build)

```bash
cp .env.example .env
make demo        # up → wait-for-healthy → seed → run the client → print the answer
```

`make demo` brings the whole stack up, seeds the synthetic Artemis data, and prints
the supply-risk answer sourced **through the gateway** with a gateway correlation id
(proving the data never left Postgres).

## Repo layout

```text
PRP.md                  # the complete build spec — read this first
CLAUDE.md               # project rules for the Claude Code build session
.claude/                # Claude Code config (settings, skills)
data/                   # synthetic Artemis generator + classification manifest
docs/                   # ARCHITECTURE / DEMO-SCRIPT / ZERO-MOVE / SECURITY / AZURE-DEPLOYMENT + whitepapers/
services/               # seeder · dab · gateway(kong) · identity · catalog · mcp
client/                 # Python CLI that queries the gateway
tools/                  # azure_pricing.py (live Azure Retail Prices helper)
observability/          # prometheus + grafana
infra/azure/            # Bicep + Azure-Gov deployment reference (not required to run)
scripts/                # demo.sh, wait-for-healthy.sh, gen-architecture-diagram.py
tests/                  # zero-move / gateway-auth / discovery / supply-risk / no-fabric
```

## Start the build (Claude Code)

1. Open this folder in a fresh Claude Code session.
2. Tell it: **"Read PRP.md and CLAUDE.md, then build this exactly, phase by phase
   (PRP §7), until every box in the Definition of Done (§13) is checked."**
3. It will scaffold the services, implement them, wire CI, write the docs, and
   validate — keeping each phase green before the next.

The synthetic data, the program narrative, and the project constraints are already
in place, so the agent can start implementing immediately.

## Constraints (enforced; see `CLAUDE.md` + `PRP.md` §9)

- No Microsoft Fabric / OneLake as a component (not in Azure Gov/GCC).
- Zero-move is real, not just claimed (Postgres/DAB network-isolated from clients).
- Azure prices are pulled **live** from the Azure Retail Prices API with a dated
  source note — never hardcoded or invented. No staffing/services dollar figures.
- All data is **synthetic** and clearly flagged. ITAR/CUI-safe.

## License

MIT — see `LICENSE`.
