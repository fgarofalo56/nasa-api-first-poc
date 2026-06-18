# PRP — NASA API-First Data Marketplace: Demo / POC Repository

> **Self-contained build spec.** Hand this entire file to a fresh Claude coding
> agent in a brand-new, empty git repository. It is everything needed to scaffold,
> implement, document, and validate a runnable proof-of-concept that demonstrates
> the Microsoft → NASA OCIO **API-first, zero-move, multi-model data marketplace**
> pattern end to end. It assumes NO prior conversation. Build it exactly as
> written; where it says "faithful," it means the local component is the
> open-source/portable analogue of the Azure-Government service, so the same
> architecture deploys to Azure Gov later with only the gateway/catalog/identity
> swapped to their managed equivalents.

---

## 1. Mission & success criteria

Build **`nasa-api-first-poc`** — a fully local, `docker compose up` demonstration of
the API-first data marketplace pattern, proven on a **synthetic
Artemis supply-chain (SAP procurement)** dataset. The demo must show, live, that:

1. **Zero data movement** — the "system of record" data never leaves its database;
   the gateway brokers every call.
2. **Auto-generated API over the system of record** — REST + GraphQL exposed
   without hand-writing an API (the Data API Builder pattern), with schema
   discovery.
3. **A governed gateway in front** — an OSS gateway (Kong) that authenticates
   (JWT/OAuth2), rate-limits, meters per-consumer call/token usage, and publishes
   the API to a catalog (the APIM-as-enterprise-gateway pattern, OSS analogue).
4. **A discoverable catalog** — the API + its OpenAPI contract, owner,
   classification, and request path are findable without tribal knowledge.
5. **A consumer answers a real mission question through the gateway** — "which
   Critical, sole-source materials on Artemis-3 are slipping > 30 days?" — via a
   Python client AND an MCP tool an agent can call, never touching the database
   directly.
6. **Observability** — per-consumer call/latency metrics on a dashboard.

**Definition of done (top-level):** `docker compose up` brings the whole stack up
healthy; a single `make demo` (or `./scripts/demo.sh`) runs the end-to-end
narrative and prints the supply-risk answer sourced through the gateway; a short
screen-recordable demo script exists; all docs render; CI is green; READMEs are
complete. See §13 for the full DoD checklist.

### Non-goals (explicitly out of scope)

- Real NASA data (all data is **synthetic**, clearly flagged), real Azure
  subscriptions, real Dataverse tenants, or production hardening.
- Microsoft Fabric or OneLake **anywhere** — they are not in Azure Government/GCC;
  do not use, install, or reference them as a component. (They may be named only in
  an "explicitly excluded, and why" sentence in docs.)
- Real cost figures beyond what the included pricing helper pulls live from the
  public Azure Retail Prices API (no auth); never hardcode or invent prices. No
  staffing/ProServe dollar figures anywhere.

---

## 2. Background — the pattern this POC demonstrates

NASA OCIO is standing up an enterprise, API-first, multi-model, **zero-copy** data
marketplace: keep data where it lives, catalog the metadata, connect compute where
needed, and avoid vendor lock-in (open formats, open-source-leaning gateway). The
first Track-A pilot is the **Artemis supply-chain (SAP procurement)** workstream.
Microsoft's role is the secure interoperability/orchestration/governance layer —
"the connective tissue, not the one AI."

This POC is the **runnable worked example** behind that story. The authored
narrative lives in `docs/` (see §11); this repo is the proof.

**Azure → OSS/local mapping (the POC builds the right-hand column; the docs explain
the left):**

| Azure-Gov target component | POC local analogue (build this) | Why faithful |
|---|---|---|
| System of record (SAP procurement) | **PostgreSQL** seeded with synthetic SAP-shaped tables | Relational SoR that stays put; data never copied out |
| Expose data as an API without writing one | **Microsoft Data API Builder (DAB)** container over Postgres | DAB is the actual MS product, MIT-licensed, runs in Docker; auto REST+GraphQL+OpenAPI |
| Azure API Management (enterprise + AI gateway) | **Kong Gateway OSS** (DB-less) in front of DAB | NASA's chosen OSS gateway; does JWT, rate-limit, key/consumer metering, request transform |
| Microsoft Entra ID (OAuth2/JWT) | Local **OIDC/JWT** issuer (a tiny signer or `mock-oauth2-server`) | Same bearer-token validation pattern at the gateway |
| Enterprise API catalog (APIM dev portal / API Center) | **Catalog service** (FastAPI) serving the OpenAPI + metadata + classification | Discoverable entry with owner/classification/request path |
| Dataverse `$metadata` discovery | DAB's `/api/openapi` + a `$metadata`-style discovery doc | Schema discovery without tribal knowledge |
| Microsoft Purview (classify + label) | A **classification manifest** (YAML) + a labeling step in the seeder | Classify BEFORE exposure (the data-quality discipline) |
| Foundry/Copilot agent consumer (MCP) | **MCP server** exposing the gateway'd query as a tool + a Python client | Agent reaches the governed surface over MCP, never the DB |
| Azure Monitor / App Insights | **Prometheus + Grafana** (Kong Prometheus plugin) | Per-consumer metering + latency dashboard |
| Azure Databricks / ADLS / Synapse / Delta | (documented only; not built) — note the gov caveat | Keep the POC focused; reference the data-platform layer in docs |

---

## 3. Tech stack (pin these)

- **Orchestration:** Docker + Docker Compose (one `docker-compose.yml`, profiles for
  `core` and `observability`).
- **System of record:** PostgreSQL 16.
- **Auto-API:** Microsoft Data API Builder (`mcr.microsoft.com/azure-databases/data-api-builder`),
  config-driven (`dab-config.json`), REST + GraphQL + OpenAPI over Postgres.
- **Gateway:** Kong Gateway 3.x OSS, **DB-less** (declarative `kong.yml`), plugins:
  `jwt`, `rate-limiting`, `prometheus`, `correlation-id`, `request-termination`
  (for OWASP-style blocks), optional `proxy-cache`.
- **Identity:** a minimal local JWT issuer — either a ~60-line Python signer service
  (RS256, publishes a JWKS) or `ghcr.io/navikt/mock-oauth2-server`. Kong's `jwt`
  plugin validates against the JWKS/consumer key.
- **Catalog + glue services:** Python 3.11 + FastAPI (catalog service; data-seeder
  job; the MCP server).
- **Synthetic data:** Python stdlib generator (port the one referenced in §5),
  deterministic/seeded, loaded into Postgres by an init job.
- **Consumer/agent:** a Python CLI client (httpx + MSAL-style bearer flow) AND an
  **MCP server** (`mcp` Python SDK) exposing one tool: `query_supply_risk`.
- **Pricing helper:** a small `azure_pricing.py` that queries the public Azure Retail
  Prices API (`https://prices.azure.com/api/retail/prices`, no auth) and prints a
  dated, source-noted table (for the "what would this cost on Azure Gov" doc/CLI).
- **Optional UI:** a tiny React + Vite single-page "Marketplace Catalog" that lists
  the cataloged data product, shows its OpenAPI, and runs the supply-risk query
  through Kong (nice-to-have; gate behind a `frontend` compose profile).
- **Lang/tooling:** Python with `ruff` + `pytest`; Make targets; pre-commit;
  GitHub Actions CI.
- **Azure path (IaC, documented + scaffolded, not required to run):** Bicep modules
  for the Azure-Gov target (APIM, Postgres Flexible Server, Container Apps for DAB,
  Entra app registration) under `infra/azure/` with a README — provide the files
  and a `what-this-would-deploy` doc; do NOT require an Azure subscription to pass CI.

---

## 4. Repository structure (create exactly this)

```text
nasa-api-first-poc/
├── README.md                      # quickstart, architecture, demo, the story
├── LICENSE                        # MIT
├── Makefile                       # up, down, seed, demo, test, lint, docs
├── docker-compose.yml             # core + observability + frontend profiles
├── .env.example                   # all config (no secrets); copy to .env
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml       # lint + tests + compose smoke
├── docs/
│   ├── ARCHITECTURE.md            # components, data flow, the Azure↔OSS mapping
│   ├── DEMO-SCRIPT.md             # the live 10-min demo narrative, step by step
│   ├── ZERO-MOVE.md               # how zero-move is proven in this POC
│   ├── AZURE-DEPLOYMENT.md        # mapping to APIM/Dataverse/Entra/ADLS on Azure Gov
│   ├── SECURITY.md                # JWT/OAuth2 flow, OWASP API Top 10 at the gateway
│   └── architecture.png           # rendered reference-architecture diagram
├── data/
│   ├── synthetic_data.py          # seeded SAP-shaped Artemis generator (port from §5)
│   ├── classification.yml         # per-table/field sensitivity labels (classify-first)
│   └── README.md                  # "SYNTHETIC — not real NASA data" banner + dictionary
├── services/
│   ├── seeder/                    # builds CSVs, applies classification, loads Postgres
│   │   ├── Dockerfile
│   │   ├── seed.py
│   │   └── schema.sql
│   ├── dab/
│   │   └── dab-config.json        # DAB entities/permissions over the procurement tables
│   ├── gateway/
│   │   └── kong.yml               # DB-less declarative config: services, routes, plugins
│   ├── identity/                  # minimal RS256 JWT issuer + JWKS (or mock-oauth2)
│   │   ├── Dockerfile
│   │   └── issuer.py
│   ├── catalog/                   # FastAPI: lists the data product + OpenAPI + metadata
│   │   ├── Dockerfile
│   │   ├── app.py
│   │   └── catalog.json           # the marketplace catalog entry (owner/classification/path)
│   └── mcp/                       # MCP server exposing query_supply_risk through the gateway
│       ├── Dockerfile
│       └── server.py
├── client/
│   ├── query_supply_risk.py       # Python CLI: get token → call gateway → print answer
│   └── README.md
├── tools/
│   └── azure_pricing.py           # live Azure Retail Prices API helper (dated source notes)
├── frontend/                      # OPTIONAL React+Vite catalog UI (frontend profile)
│   └── ...
├── observability/
│   ├── prometheus.yml
│   └── grafana/                   # dashboard provisioning (per-consumer calls + latency)
├── scripts/
│   ├── demo.sh                    # the end-to-end demo runner (make demo)
│   ├── wait-for-healthy.sh
│   └── gen-architecture-diagram.py
└── tests/
    ├── test_zero_move.py          # proves data is only ever read through the gateway
    ├── test_gateway_auth.py       # 401 without JWT, 200 with, 429 over rate limit
    ├── test_discovery.py          # OpenAPI/$metadata discovery returns the schema
    ├── test_supply_risk.py        # the query returns the expected high-risk rows
    └── test_no_fabric.py          # asserts no "fabric"/"onelake" as a component anywhere
```

---

## 5. Synthetic Artemis dataset (port this generator)

Implement `data/synthetic_data.py` as a **deterministic (seeded), pure-stdlib**
SAP-shaped procurement generator. It is ITAR/CUI-safe: every vendor name carries a
`(SYNTHETIC)` suffix, no real NASA content. Produce four tables + a data dictionary:

- `vendors` (LFA1-style): `LIFNR, NAME1, CAGE_CODE, REGIO, LAND1, SOLE_SOURCE,
  PAST_PERF_SCORE, SMALL_BUSINESS` — ~26 rows, ~22% sole-source.
- `materials` (MARA-style): `MATNR, MAKTX, MATKL, PROGRAM, CRITICALITY,
  STD_LEAD_TIME_DAYS, STD_UNIT_COST_USD, UOM` — ~60 rows across programs
  {SR1-Freedom, Moon-Base, Artemis-3, Gateway, EGS-Ground} and criticalities
  {Critical, Essential, Routine}.
- `purchase_orders` (EKKO/EKPO-style): `EBELN, EBELP, MATNR, MAKTX, LIFNR, PROGRAM,
  CRITICALITY, MENGE, MEINS, NETPR, NETWR, WAERS, EINDT (promised), BEDAT (PO date),
  ACTUAL_DELIVERY, DELAY_DAYS, PAD_ANOMALY, STATUS` — ~240 rows; delay probability
  rises with criticality + sole-source; ~3% "pad anomaly" shock adds 60-240 days.
- `supply_risk` (derived): per-material `RISK_SCORE` (0-100) + `RISK_TIER`
  (High≥70/Medium≥40/Low) from sole-source + criticality + avg delay; sorted desc.

With `seed=42` the result must be reproducible (≈14 sole-source materials, ≈11
High-tier). The data dictionary (`data/README.md`) leads with a **"SYNTHETIC — NOT
REAL NASA PROCUREMENT"** banner and documents every SAP field.

> **Already provided.** A working, pure-stdlib generator is pre-copied to
> `data/synthetic_data.py` — `generate_artemis_procurement(out_dir, seed=42)` writes
> the four CSVs + the Markdown data dictionary. The seeder calls it. You do not need
> any external repo; use this file as-is (or refine it).

`data/classification.yml` assigns a sensitivity label to each table/field (e.g.
`purchase_orders.NETPR → Confidential`, `materials.MAKTX → Routine`,
`vendors.SOLE_SOURCE → Sensitive`). The seeder applies these as Postgres
`COMMENT ON COLUMN` + emits them into the catalog entry — **classification happens
before exposure** (the core data-quality discipline).

---

## 6. The four asset-class flow (what each service does)

The demo is the **expose → façade → catalog → consume** zero-move pattern as a
left-to-right flow. Implement each station:

1. **Expose (SoR stays put).** Postgres holds the procurement tables. Nothing copies
   them out. Network policy in compose: Postgres is on an internal network reachable
   ONLY by DAB — not by the gateway, not by clients. (This is the zero-move proof:
   the only path to data is DAB→Kong.)
2. **Façade (auto-API).** DAB reads `dab-config.json` and exposes REST
   (`/api/Material`, `/api/SupplyRisk`, …) + GraphQL + OpenAPI (`/api/openapi`) over
   Postgres, with OData-style `$select/$filter/$orderby` and per-entity read
   permissions. No hand-written API. DAB is reachable only by Kong (internal
   network) — consumers cannot hit DAB directly.
3. **Govern + publish (gateway + catalog).** Kong (DB-less `kong.yml`) fronts DAB:
   a `service` → DAB, `routes` for the procurement API, and plugins: `jwt` (reject
   no/invalid token at the edge — request never reaches DAB), `rate-limiting`
   (429 + `Retry-After` over the cap), `prometheus` (per-consumer metrics),
   `correlation-id`, and a `request-termination`/`pre-function` guard demonstrating
   one OWASP-API-Top-10 control (e.g. block wildcard/over-broad queries). The
   **catalog** service publishes the data product: its OpenAPI (proxied from DAB
   through Kong), owner, classification (from `classification.yml`), and the request
   path — a discoverable entry at `GET /catalog` and `GET /catalog/artemis-supply-risk`.
4. **Consume (governed clients).** `client/query_supply_risk.py` obtains a bearer
   token from the identity issuer, then calls **through Kong** to answer the mission
   question. The **MCP server** exposes the same query as a tool `query_supply_risk`
   so an agent (Claude/Copilot/etc.) reaches the governed surface over MCP — never
   the DB. Token usage is metered per consumer at the gateway.

**The headline query (must work end to end):**
> "Which Critical, sole-source materials on Artemis-3 have an average delay > 30
> days?" → resolves to an OData-style call through Kong against `SupplyRisk`
> (`$filter=program eq 'Artemis-3' and criticality eq 'Critical' and sole_source eq
> true and avg_delay_days gt 30 &$orderby=risk_score desc`) and prints the ranked
> high-risk parts + their suppliers.

---

## 7. Implementation phases (milestones + acceptance criteria)

Build in this order; each phase ends green before the next.

**Phase 0 — Scaffold.** Repo tree (§4), `README` skeleton, `Makefile`, `.env.example`,
pre-commit, CI that lints + runs (initially trivial) tests. **AC:** `make lint` and
`make test` pass on an empty stack; CI green.

**Phase 1 — Data + SoR.** `synthetic_data.py`, `classification.yml`,
`services/seeder` (schema.sql + seed.py), Postgres in compose. **AC:** `make seed`
loads ≈26/60/240/≈59 rows; column comments carry classifications;
`tests/test_supply_risk.py` can query Postgres directly (temporarily) and confirm
the expected High-tier Artemis-3 rows exist.

**Phase 2 — Auto-API (DAB).** `dab-config.json` exposing the four entities with read
permissions + OData query options; DAB container wired to Postgres on the internal
network. **AC:** through DAB (temporarily exposed) `/api/SupplyRisk?$filter=...`
returns the high-risk rows and `/api/openapi` returns a schema; then LOCK DAB to the
internal network.

**Phase 3 — Identity + Gateway.** Identity issuer (RS256 + JWKS) and Kong DB-less
config with `jwt` + `rate-limiting` + `prometheus`. Consumers reach the API ONLY via
Kong. **AC:** `tests/test_gateway_auth.py` — no token → 401 (DAB never hit), valid
token → 200, exceed the rate cap → 429 with `Retry-After`. DAB + Postgres are
unreachable from the client network (`tests/test_zero_move.py`).

**Phase 4 — Catalog + discovery.** Catalog FastAPI service serving the marketplace
entry + the OpenAPI (proxied via Kong) + classification + owner + request path.
**AC:** `tests/test_discovery.py` — `GET /catalog` lists the product; the OpenAPI
documents the entities; classifications are present.

**Phase 5 — Consumers.** `client/query_supply_risk.py` (token→gateway→answer) and the
MCP server tool. **AC:** `make demo` runs the full narrative and prints the supply-risk
answer; the MCP tool returns the same data when invoked.

**Phase 6 — Observability.** Prometheus scraping Kong + a Grafana dashboard
(per-consumer call count + p50/p95 latency). **AC:** dashboard shows traffic after a
demo run (manual verification documented in DEMO-SCRIPT.md).

**Phase 7 — Docs + Azure path + diagram.** All `docs/`, `gen-architecture-diagram.py` → `docs/architecture.png`, `tools/azure_pricing.py`
with a live dated table, and `infra/azure/` Bicep + AZURE-DEPLOYMENT.md. **AC:** all
docs present + accurate; `azure_pricing.py` prints live prices with the exact dated
source note (§9); `test_no_fabric.py` passes.

**Phase 8 (optional) — Catalog UI.** React+Vite SPA behind the `frontend` profile.
**AC:** lists the product, shows OpenAPI, runs the query through Kong from the browser.

---

## 8. Key file specs (give the coding agent precise contracts)

- **`docker-compose.yml`** — networks: `internal` (postgres↔dab↔kong-upstream) and
  `edge` (kong↔clients/catalog/mcp). Postgres and DAB attach ONLY to `internal`
  (+ kong bridges). Profiles: `core` (postgres, seeder, dab, identity, kong, catalog,
  mcp), `observability` (prometheus, grafana), `frontend` (ui). Healthchecks on every
  service; `depends_on: condition: service_healthy`.
- **`services/dab/dab-config.json`** — `data-source` = Postgres conn from env;
  `entities`: `Material`, `Vendor`, `PurchaseOrder`, `SupplyRisk` each mapped to its
  table, `permissions: [{ role: anonymous, actions: [read] }]`, REST + GraphQL
  enabled, OpenAPI enabled. (DAB enforces read-only; Kong enforces auth.)
- **`services/gateway/kong.yml`** — `_format_version: "3.0"`; one `service` →
  `http://dab:5000`; `routes` for `/api/...`; plugins `jwt` (consumers with RSA
  public keys / JWKS), `rate-limiting` (e.g. `minute: 60`, `policy: local`),
  `prometheus`, `correlation-id`; a `pre-function` or `request-termination` showing
  one OWASP-API control. Define 2 `consumers` (e.g. `analyst`, `artemis-agent`) with
  JWT credentials so per-consumer metering is visible.
- **`services/identity/issuer.py`** — `/.well-known/jwks.json` + `POST /token`
  (issues an RS256 JWT with `iss/aud/sub/exp` for a requested consumer). Keep it
  tiny; this stands in for Entra ID.
- **`services/catalog/app.py`** — `GET /catalog`, `GET /catalog/{id}` returning
  `{id, title, owner, classification, openapi_url (via Kong), request_path,
  sample_query}`; reads `catalog.json` + merges `data/classification.yml`.
- **`services/mcp/server.py`** — one MCP tool `query_supply_risk(program, min_delay)`
  that fetches a token from identity, calls Kong, returns rows. Document how to point
  Claude Desktop / an MCP host at it.
- **`client/query_supply_risk.py`** — `argparse` (`--program Artemis-3
  --min-delay 30`), bearer flow, calls Kong, pretty-prints the ranked answer + the
  gateway correlation id (proves it went through the gateway).
- **`Makefile`** — `up`, `down`, `seed`, `demo`, `test`, `lint`, `docs`, `diagram`,
  `pricing`. `make demo` = up → wait-for-healthy → seed → run client → run MCP smoke
  → print "data never left Postgres; brokered via Kong (corr-id …)".

---

## 9. Hard constraints (enforce; CI checks where possible)

- **No Microsoft Fabric / OneLake** as a component or recommendation anywhere
  (`test_no_fabric.py` greps the repo). A single "explicitly excluded — not in Azure
  Gov/GCC — use Databricks/ADLS/Synapse/Delta instead" sentence in docs is allowed.
- **Zero-move is real, not just claimed** — Postgres/DAB are network-isolated from
  clients; the ONLY data path is through Kong (`test_zero_move.py`).
- **Pricing is live + dated, never invented** — `tools/azure_pricing.py` hits the
  Azure Retail Prices API and every figure carries exactly:
  `"Source: Azure Retail Prices API, list price (PAYG), <region>, retrieved
  <YYYY-MM-DD>; excludes EA/MCA/commit discounts."` No staffing/ProServe dollars.
- **Synthetic only** — the data banner is present; no real-data ingestion paths.
- **Gateway framed vendor-neutral** in docs — Kong (OSS) is the built path; APIM
  (managed) is the documented Azure-Gov equivalent; competitors are not named in
  comparisons.
- **Open standards** — OData-style REST, OpenAPI, OAuth2/JWT, MCP. No proprietary
  client required to consume the API.

---

## 10. Validation & testing

- `pytest` suite (the `tests/` files in §4) must pass in CI.
- CI `compose smoke`: `docker compose --profile core up -d` → `wait-for-healthy` →
  run `client/query_supply_risk.py` → assert the known High-tier Artemis-3 rows are
  returned → `docker compose down`.
- Manual visual check documented in `DEMO-SCRIPT.md`: Grafana shows per-consumer
  traffic after a demo run.
- Lint: `ruff check` + `ruff format --check` clean.

---

## 11. Documentation

This is a **standalone sample/demo** — there is no customer-deliverable / whitepaper
content. All documentation lives in `docs/` (ARCHITECTURE, DEMO-DAY, DEMO-SCRIPT,
ZERO-MOVE, SECURITY, ADD-A-SOURCE, GRAPHQL, AZURE-*, APIM-*, DATABRICKS, POWERBI,
DISCLAIMER) and `README.md`. `docs/ARCHITECTURE.md` includes the Azure↔OSS mapping
table (§2) so a reader sees how the local POC maps to the Azure-Gov target. The
`README.md` opens with the one-sentence frame ("one platform for data, APIs, and code;
Microsoft as the interoperability layer, not the one AI"), a 60-second quickstart
(`cp .env.example .env && make demo`), the architecture diagram, and the demo narrative.
All data is synthetic — see `docs/DISCLAIMER.md`.

---

## 12. Azure-Government deployment path (scaffold + document; not required to run)

Under `infra/azure/` provide Bicep modules + `AZURE-DEPLOYMENT.md` describing the
managed target: **Azure API Management** (replaces Kong; map the same JWT/rate-limit/
metering policies, and note APIM's AI-gateway `llm-token-limit`/`llm-emit-token-metric`
for the LLM-gateway story), **Dataverse Web API** or **Data API Builder on Container
Apps** (replaces local DAB; note Dataverse `$metadata` discovery), **Microsoft Entra
ID** (replaces the local issuer), **PostgreSQL Flexible Server / Azure SQL** (SoR),
**Microsoft Purview** (catalog + classification), and **Azure Databricks with
managed Unity Catalog + Databricks SQL + Delta Lake + Delta Sharing on ADLS Gen2 +
Azure Synapse** for the data-platform layer. **Posture note:** the primary
deployment is **commercial (global) Azure at FedRAMP High** — where the full
*managed* Databricks platform (managed Unity Catalog + Databricks SQL) is available;
the managed-UC / Databricks-SQL gap applies **only** to the Azure Government regions
(US Gov Arizona / US Gov Virginia), an ITAR / strict-CUI subset, where open-source
Unity Catalog or Microsoft Purview is the catalog fallback. Data classification
drives the boundary, not vendor preference. CI must NOT require an Azure
subscription; these are reference IaC + docs.

---

## 13. Definition of done (checklist)

- [ ] `cp .env.example .env && docker compose --profile core up` → all services
      healthy; `make demo` prints the Artemis-3 supply-risk answer sourced through
      Kong with a gateway correlation id.
- [ ] No-token call → 401 (DAB never reached); valid token → 200; over-limit → 429.
- [ ] Postgres + DAB are unreachable from the client network (zero-move proven by test).
- [ ] DAB OpenAPI + the catalog entry expose the schema, owner, classification, and
      request path (discovery works).
- [ ] MCP tool `query_supply_risk` returns the same governed answer.
- [ ] Grafana dashboard shows per-consumer traffic after a run.
- [ ] `tools/azure_pricing.py` prints live Azure-Gov prices with the exact dated
      source note; no staffing dollars anywhere.
- [ ] `test_no_fabric.py` passes (no Fabric/OneLake as a component).
- [ ] All `docs/` complete (ARCHITECTURE/DEMO-SCRIPT/ZERO-MOVE/SECURITY/AZURE-DEPLOYMENT);
      `docs/architecture.png` rendered.
- [ ] `infra/azure/` Bicep + AZURE-DEPLOYMENT.md present.
- [ ] `ruff` clean; `pytest` green; CI (lint + tests + compose smoke) green.
- [ ] README quickstart works from a clean clone on a machine with only Docker.

---

## 14. References (official sources behind the design — keep these in docs)

All Microsoft sources are official documentation; verify each resolves before
quoting in docs. (Kong + Delta/Unity are their projects' official docs.)

- Data API Builder overview — <https://learn.microsoft.com/azure/data-api-builder/overview>
- What is Azure API Management? — <https://learn.microsoft.com/azure/api-management/api-management-key-concepts>
- AI gateway capabilities in API Management — <https://learn.microsoft.com/azure/api-management/genai-gateway-capabilities>
- Mitigate OWASP API Security Top 10 with API Management — <https://learn.microsoft.com/azure/api-management/mitigate-owasp-api-threats>
- Self-hosted gateway overview (zero-move enabler) — <https://learn.microsoft.com/azure/api-management/self-hosted-gateway-overview>
- Dataverse Web API overview — <https://learn.microsoft.com/power-apps/developer/data-platform/webapi/overview>
- Web API service documents ($metadata / CSDL) — <https://learn.microsoft.com/power-apps/developer/data-platform/webapi/web-api-service-documents>
- About MCP servers in API Management — <https://learn.microsoft.com/azure/api-management/mcp-server-overview>
- Microsoft Purview Information Protection — <https://learn.microsoft.com/purview/information-protection>
- FedRAMP — Azure compliance — <https://learn.microsoft.com/azure/compliance/offerings/offering-fedramp>
- What is Azure Government? — <https://learn.microsoft.com/azure/azure-government/documentation-government-welcome>
- Azure Databricks feature region support (UC/Databricks SQL NOT in Gov) — <https://learn.microsoft.com/azure/databricks/resources/feature-region-support>
- Delta Lake (Azure Databricks) — <https://learn.microsoft.com/azure/databricks/delta/>
- Kong Gateway (hybrid/DB-less) — <https://developer.konghq.com/gateway/>
- Kong resource sizing guidelines — <https://developer.konghq.com/gateway/resource-sizing-guidelines/>
- Azure Retail Prices API — <https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices>

---

## 15. Build instructions for the coding agent (read first)

1. Initialize the repo, scaffold §4, and commit per phase (§7) with conventional
   messages; keep CI green at every phase.
2. Build the OSS/local stack (§3, §6). Use the exact Azure↔OSS mapping (§2) so the
   architecture is faithful and the Azure path (§12) is a clean swap.
3. Honor every hard constraint (§9); wire the CI checks (§10).
4. Write the repo docs (§11) so a reader understands both the story and the running proof.
5. Finish only when every box in §13 is checked. Then write a short
   `docs/DEMO-SCRIPT.md` a presenter can follow live in ~10 minutes.

> This POC is a runnable sample of the API-first pattern:
> data stays in its system of record, an OSS gateway governs a auto-generated API in
> front of it, the data product is discoverable in a catalog, and an agent answers a
> real Artemis supply-chain question through the gateway — with a documented,
> one-swap path to the Azure-Government managed equivalents.
