# 🏛️ Architecture

[Home](../README.md) > [Documentation](README.md) > **Architecture**

The POC builds the **local / open-source analogue** of each Azure-Government target
service, so the same architecture promotes to Azure later by swapping the gateway,
catalog, and identity for their managed equivalents — the *pattern* is identical.

> [!NOTE]
> **TL;DR** — A client (or MCP agent) presents a bearer token to **Kong**, the *only*
> path to the data. Kong validates the JWT, rate-limits + meters the call, and proxies
> to **Data API Builder**, which serves auto-generated REST/GraphQL over **PostgreSQL**.
> Postgres and DAB live on an internal Docker network and are unreachable from clients —
> that is the **zero-move** guarantee. All data is **synthetic** (see
> [`DISCLAIMER.md`](DISCLAIMER.md)).

## 📑 Table of Contents

- [🏗️ The zero-move flow](#️-the-zero-move-flow)
- [🔀 Azure ↔ OSS/local mapping](#-azure--osslocal-mapping)
- [🌐 Networks (docker-compose)](#-networks-docker-compose)
- [✨ Multi-source federation + control-plane](#-multi-source-federation--control-plane)

---

## 🏗️ The zero-move flow

```mermaid
flowchart TD
    CLI["client / MCP agent<br/>(bearer token from local issuer)"]
    KONG["Kong gateway (OSS)<br/>JWT · rate-limit · meter · correlation-id<br/>(only path to data)"]
    DAB["Data API Builder (DAB)<br/>auto REST + GraphQL + OpenAPI"]
    PG[("PostgreSQL — system of record<br/>data NEVER leaves here<br/>(synthetic SAP Artemis procurement)")]
    CAT["Catalog service<br/>publishes OpenAPI · owner · classification · request path"]
    OBS["Prometheus / Grafana<br/>per-consumer call + latency metrics"]
    CLI --> KONG
    KONG -->|REST / OData| DAB
    DAB -->|internal network only<br/>unreachable from clients| PG
    KONG -.-> CAT
    KONG -.-> OBS
    style KONG fill:#cce5ff
    style PG fill:#d4edda
```

<details>
<summary>ASCII version of the same flow</summary>

```text
   client / MCP agent
          │  (bearer token from the local issuer)
          ▼
   ┌──────────────┐   only path to data
   │  Kong (OSS)  │   JWT · rate-limit · meter · correlation-id
   │   gateway    │
   └──────┬───────┘
          │ REST / OData
          ▼
   ┌──────────────┐   auto-generated REST + GraphQL + OpenAPI (no hand-written API)
   │ Data API     │
   │ Builder (DAB)│
   └──────┬───────┘
          │  (internal network only — unreachable from clients)
          ▼
   ┌──────────────┐   system of record — data NEVER leaves here
   │  PostgreSQL  │   (synthetic SAP-shaped Artemis procurement)
   └──────────────┘

   catalog service ── publishes the OpenAPI + owner + classification + request path
   prometheus/grafana ── per-consumer call + latency metrics
```

</details>

Postgres and DAB attach **only** to an internal Docker network; the sole path to the
data for any client is **through Kong**. That is the zero-move proof (see
[`ZERO-MOVE.md`](ZERO-MOVE.md) + [`tests/test_zero_move.py`](../tests/test_zero_move.py)).

## 🔀 Azure ↔ OSS/local mapping

| Azure-Gov target component | POC local analogue (built here) | Why faithful |
|---|---|---|
| System of record (SAP procurement) | **PostgreSQL** seeded with synthetic SAP-shaped tables | Relational SoR that stays put; data never copied out |
| Expose data as an API without writing one | **Microsoft Data API Builder (DAB)** over Postgres | DAB is the actual MS product (MIT); auto REST+GraphQL+OpenAPI |
| Azure API Management (enterprise + AI gateway) | **Kong Gateway OSS** (DB-less) in front of DAB | The chosen OSS gateway; JWT, rate-limit, consumer metering |
| Microsoft Entra ID (OAuth2/JWT) | local **OIDC/JWT** issuer (RS256 + JWKS) | Same bearer-token validation pattern at the gateway |
| Enterprise API catalog (APIM dev portal / API Center) | **catalog** service (FastAPI) | Discoverable entry with owner/classification/request path |
| Dataverse `$metadata` discovery | DAB `/api/openapi` + a `$metadata`-style discovery doc | Schema discovery without tribal knowledge |
| Microsoft Purview (classify + label) | `data/classification.yml` applied at seed | Classify BEFORE exposure |
| Foundry/Copilot agent consumer (MCP) | **MCP server** + Python client | Agent reaches the governed surface, never the DB |
| Azure Monitor / App Insights | **Prometheus + Grafana** | Per-consumer metering + latency dashboard |
| Azure data platform (Databricks/Delta/UC) | documented only — see [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md) | Managed UC + Databricks SQL at FedRAMP High in commercial Azure |

## 🌐 Networks (docker-compose)

Two Docker networks enforce zero-move. `kong` is the **only** service attached to both,
so the sole path from any client to the data is through the gateway.

| Network | `internal:` flag | Services attached | Purpose |
|---|---|---|---|
| `internal` | `internal: true` (no egress) | `postgres`, `seeder`, `dab`, `transportation`, `kong` | Sources live here with **no host ports** — unreachable from clients |
| `edge` | bridge | `kong`, `identity`, `catalog`, `registry`, `mcp`, `prometheus`, `grafana`, `frontend` | Consumers / UI / control-plane reach any source **only via Kong** |

> [!IMPORTANT]
> Because `postgres` and `dab` publish **no host ports** and sit on the `internal`
> (egress-disabled) network, the only reachable surface is Kong on `edge`. This is the
> zero-move proof — verified by [`tests/test_zero_move.py`](../tests/test_zero_move.py).

## ✨ Multi-source federation + control-plane

The gateway fronts **multiple** sources. Beyond the built-in Artemis system of record,
an **onboarding wizard** publishes additional existing APIs (e.g. the DOT transportation
DAB API) through the same gateway at runtime — the API-Management / API-Center pattern.

```mermaid
flowchart LR
    UI["NASA-themed UI<br/>(onboarding wizard)"] -->|POST /sources| REG["Registry /<br/>control-plane"]
    REG -->|hot-reload POST /config| KONG["Kong gateway"]
    KONG -->|/api/* governed| DAB["DAB → Postgres<br/>(Artemis SoR)"]
    KONG -->|/dot/* governed| DOT["DOT Transportation API<br/>(2nd source)"]
    CLI["Consumer + token"] --> KONG
    CAT["Catalog"] -. lists both .- KONG
```

- **`services/registry`** — reads the running base config (rendered with the live RSA
  key), merges a Kong `service`+`route`+plugins for each registered source, and hot-reloads
  Kong's DB-less config via the admin `/config` endpoint. No restart, no source change.
- **`services/transportation`** — a DOT-flavored DAB-style API (synthetic bridge
  inventory) that stands in for the published Azure DAB demo; internal-only like the SoR.
- Every added source inherits the same governance (JWT, per-consumer rate-limit,
  correlation id, CORS). See [`ADD-A-SOURCE.md`](ADD-A-SOURCE.md).

> [!TIP]
> See [`PRP.md`](../PRP.md) §2 and §6 for the full component contracts, and
> [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md) for the managed-Azure promotion path.
