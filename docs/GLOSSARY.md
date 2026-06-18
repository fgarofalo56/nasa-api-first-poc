# 📖 Glossary — every term & acronym in this repo

[Home](../README.md) > [Documentation](README.md) > **Glossary**

> [!WARNING]
> **Illustrative reference · sample/synthetic data only · not an official NASA
> document.** All data, vendors, prices, and scenarios are **synthetic** — see
> [`DISCLAIMER.md`](DISCLAIMER.md) before sharing or adapting.

> [!NOTE]
> **TL;DR** — This is the plain-language dictionary for the whole project. Every term,
> acronym, product, and field name that shows up in the code or docs is defined here once,
> in everyday English, with a pointer to *where* it appears so you can go read the real
> thing next. If a doc uses a word you don't recognise, look here first.

**How to read this glossary.** The project tells one story: *expose an existing database
as a governed API so consumers can ask it questions without ever copying the data out*
("zero-move"). Almost every term below is one moving part of that story. We group the
terms the way the story unfolds — first the **big idea**, then the **local building
blocks** you run with Docker, then their **Azure managed twins**, then the **identity &
security** vocabulary, then the **data/analytics platform**, and finally the
**supply-chain domain** field names in the synthetic dataset. Within each group terms are
ordered so earlier ones explain later ones.

---

## 📑 Table of Contents

- [🧭 The core idea](#-the-core-idea)
- [🧱 Local / open-source building blocks (the dev-test stack)](#-local--open-source-building-blocks-the-dev-test-stack)
- [☁️ Azure managed twins (the real demo target)](#️-azure-managed-twins-the-real-demo-target)
- [🪪 Identity, tokens & API security](#-identity-tokens--api-security)
- [🗄️ Data & analytics platform (the lakehouse story)](#️-data--analytics-platform-the-lakehouse-story)
- [📦 Procurement domain & dataset fields (SAP-shaped)](#-procurement-domain--dataset-fields-sap-shaped)
- [🛠️ Project tooling & conventions](#️-project-tooling--conventions)
- [🔤 Quick acronym index](#-quick-acronym-index)

---

## 🧭 The core idea

> **Why this section exists:** everything else is an implementation detail of these few
> ideas. Get these and the rest of the project reads as "how we actually did it."

### API-first

**API-first** means you treat the **API** (Application Programming Interface — a defined
contract other software calls to read or change data) as the *primary product*, designed
and governed before anyone writes a consuming app. In this repo the database is never
shared directly; the only thing consumers ever see is a documented API contract.
*In plain terms:* the API is the front door, and there is no back door.
*Where it appears:* the project name `nasa-api-first-poc`, [`README.md`](../README.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md).

### Zero-move (zero-copy)

**Zero-move** is the headline guarantee: the source data **never leaves its home
database**. Consumers get answers by calling the API; no bulk export, no second copy to
keep in sync, no copy to secure separately. *Why this matters:* every copy of sensitive
data is a new place it can leak and a new thing that can drift out of date — eliminating
copies is both a security win and a data-quality win. In this POC it is **proven, not just
claimed**: Postgres and the auto-API sit on an isolated network with no host ports, so the
gateway is the *only* path in. *Where it appears:* [`ZERO-MOVE.md`](ZERO-MOVE.md),
[`tests/test_zero_move.py`](../tests/test_zero_move.py), [`ARCHITECTURE.md`](ARCHITECTURE.md).

### Data marketplace

A **data marketplace** is a catalog of governed, discoverable **data products** that
approved consumers can find, understand, and call — each with a known owner, contract, and
classification. *In plain terms:* an internal "app store," but for trustworthy datasets
instead of apps. *Where it appears:* [`README.md`](../README.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md), the catalog service.

### Data product

A **data product** is one packaged, governed dataset exposed through the API — e.g. the
Artemis supply-risk view — with an owner, a documented contract, and a classification.
Analytics tools consume the *product*, not the raw database. *Where it appears:*
[`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md), the catalog.

### System of record (SoR)

The **system of record** is the authoritative source database where the data actually
lives and stays. Here it is **PostgreSQL**, seeded with synthetic, SAP-shaped procurement
tables. Zero-move means the SoR is the *only* copy. *Where it appears:* nearly every doc;
defined in [`ARCHITECTURE.md`](ARCHITECTURE.md).

### Control plane / data plane

The **data plane** is the path that actual data requests travel (consumer → gateway →
auto-API → database). The **control plane** is the management path that *configures* that
data path — e.g. registering a new source so the gateway will route to it. In this repo
the `registry` service is the control plane and Kong's proxy is the data plane.
*Where it appears:* [`ARCHITECTURE.md`](ARCHITECTURE.md) ("Multi-source federation +
control-plane"), [`ADD-A-SOURCE.md`](ADD-A-SOURCE.md).

### Federation / multi-source

**Federation** here means one gateway fronts **multiple** independent source APIs (the
Artemis SoR *and* a second "DOT transportation" source), so consumers query many sources
through a single governed entry point — without merging or copying the underlying
databases. *Where it appears:* [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`ADD-A-SOURCE.md`](ADD-A-SOURCE.md), `services/transportation`, `services/registry`.

---

## 🧱 Local / open-source building blocks (the dev-test stack)

> **Why this section exists:** you run these with `docker compose` to develop and test the
> pattern on your laptop. Each one is the open-source **analogue** of an Azure managed
> service (covered in the next section). *Frame it as:* run it locally to build and test;
> deploy the managed twins to Azure for the real demo.

### Docker / Docker Compose

**Docker** packages each service into a self-contained **container** (an isolated process
with its own filesystem and dependencies). **Docker Compose** runs several containers
together from one `docker-compose.yml` file, wiring up their networks and start-up order.
`docker compose up` brings the whole demo stack to life. *Where it appears:*
[`docker-compose.yml`](../docker-compose.yml), [`README.md`](../README.md).

### PostgreSQL (Postgres / PG)

**PostgreSQL** (often "Postgres," abbreviated **PG**) is a popular open-source relational
database. Here, pinned to **version 16**, it is the system of record holding the synthetic
procurement tables. It attaches *only* to the internal network with no host port — you
cannot reach it from outside. *Where it appears:* [`docker-compose.yml`](../docker-compose.yml),
[`.env.example`](../.env.example), `services/seeder`.

### DAB — Data API Builder

**Data API Builder (DAB)** is a real Microsoft open-source product (MIT-licensed) that
points at a database and **auto-generates a REST and GraphQL API** plus an OpenAPI
description — *no hand-written API code*. *Why this matters:* it is what makes "expose the
database as an API" a config exercise instead of a build project, and it is the same
product you would run in Azure. *In plain terms:* you give it a connection string and a
list of tables, and it hands you a working API. *Where it appears:*
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`GRAPHQL.md`](GRAPHQL.md),
[`services/dab/dab-config.json`](../services/dab/dab-config.json).

### Kong (Kong Gateway OSS)

**Kong** is the open-source **API gateway** used here in **DB-less** mode (its config is a
single declarative file, no database of its own). An **API gateway** is the guard at the
front door: it sits between consumers and the API, and on every call it validates the
token, enforces rate limits, meters usage per consumer, stamps a correlation id, and only
then proxies to the auto-API. In this POC Kong is the **only** service on both networks, so
it is the single path to the data. *Where it appears:*
[`services/gateway/kong.yml`](../services/gateway/kong.yml),
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`SECURITY.md`](SECURITY.md). Its Azure twin is
**APIM** (below).

### Kong plugin

A **plugin** is a unit of behaviour Kong applies to a route. The ones used here:

| Plugin | What it does in this POC |
|---|---|
| `jwt` | Verifies the RS256 token signature + expiry; maps the call to a consumer via the `client_id` claim. |
| `rate-limiting` | Caps calls per consumer (default 60/min); over the limit returns **429** + `Retry-After`. |
| `correlation-id` | Stamps a unique id on every request so a call can be traced end to end. |
| `pre-function` | A small guard that blocks over-broad pulls (e.g. `$first > 200` → **400**). |
| `cors` | Allows the browser UI to call the gateway (Cross-Origin Resource Sharing). |
| `prometheus` | Exposes per-consumer metrics for the dashboards. |

*Where it appears:* [`SECURITY.md`](SECURITY.md),
[`services/gateway/kong.yml`](../services/gateway/kong.yml).

### Identity issuer (local OIDC/JWT issuer)

The **identity issuer** (`services/identity`) is a small local service that **mints
short-lived bearer tokens** for the demo consumers and publishes the public key Kong uses
to validate them. It is the local stand-in for **Microsoft Entra ID**. It generates its
signing key at runtime and never commits it. *Where it appears:*
[`services/identity/README.md`](../services/identity/README.md),
[`SECURITY.md`](SECURITY.md). (See **OIDC**, **JWT**, **JWKS**, **RS256** below.)

### Catalog service

The **catalog** (`services/catalog`, a FastAPI app) is the discovery surface: it publishes
each data product's OpenAPI contract, **owner**, **classification**, and **request path**,
so consumers can find and understand an API without tribal knowledge. It is the local twin
of the **APIM Developer Portal / Azure API Center**. *Where it appears:*
[`services/catalog/README.md`](../services/catalog/README.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md).

### Registry service (control-plane / onboarding wizard)

The **registry** (`services/registry`) is the control plane behind the "add a source"
wizard. It reads Kong's running config, merges in a service + route + plugins for each
newly registered source, and **hot-reloads** Kong (via Kong's admin `/config` endpoint) —
no restart, no change to the source. *Where it appears:*
[`ADD-A-SOURCE.md`](ADD-A-SOURCE.md), [`ARCHITECTURE.md`](ARCHITECTURE.md),
`services/registry/app.py`.

### Seeder

The **seeder** (`services/seeder`) is a one-shot job that loads the synthetic dataset into
Postgres and applies the classification labels as column comments — i.e. it **classifies
before exposure**. It calls `data/synthetic_data.py` (do not rewrite that generator).
*Where it appears:* `services/seeder`, [`SECURITY.md`](SECURITY.md).

### Transportation service

The **transportation** service (`services/transportation`) is a second, DOT-flavoured
(Department of Transportation) DAB-style API over synthetic bridge-inventory data. It
exists to prove **multi-source federation** — a second source published through the same
gateway. Like the SoR, it is internal-only. *Where it appears:*
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`ADD-A-SOURCE.md`](ADD-A-SOURCE.md).

### MCP — Model Context Protocol

**MCP (Model Context Protocol)** is an open standard for giving AI assistants **tools**
they can call. An **MCP server** advertises tools; an **MCP host** (e.g. Claude Desktop,
Microsoft Copilot, Azure AI Foundry) calls them. This repo's MCP server
(`services/mcp`) exposes one tool, `query_supply_risk`, that answers the supply-chain
question **through the gateway** — so an AI agent gets the *same governed answer* a human
does, and never touches the database. *Where it appears:*
[`services/mcp/README.md`](../services/mcp/README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md).

### FastMCP

**FastMCP** is the helper in the Python `mcp` SDK used to build the MCP server with minimal
boilerplate (you decorate a Python function and it becomes a callable tool). *Where it
appears:* [`services/mcp/README.md`](../services/mcp/README.md), `services/mcp/server.py`.

### MCP transport (stdio / streamable-http)

A **transport** is how an MCP host and server talk. **`stdio`** pipes messages over
standard input/output (how a desktop host launches a local server as a subprocess).
**`streamable-http`** carries them over HTTP (how this server runs under Docker, on
`/mcp`). *Where it appears:* [`services/mcp/README.md`](../services/mcp/README.md).

### Prometheus

**Prometheus** is an open-source monitoring system that **scrapes** numeric metrics (like
"calls per consumer") from services and stores them as time series. Kong's `prometheus`
plugin feeds it. Its Azure twin is **Azure Monitor**. *Where it appears:*
`observability/`, [`docker-compose.yml`](../docker-compose.yml).

### Grafana

**Grafana** is an open-source dashboard tool that **visualizes** the metrics Prometheus
collects — here, per-consumer traffic and latency charts. *Where it appears:*
`observability/`, [`ARCHITECTURE.md`](ARCHITECTURE.md). On Azure the dashboards live in
**Azure Monitor / Application Insights**.

### FastAPI

**FastAPI** is the Python web framework used to build the small services (catalog,
identity, registry, seeder). It auto-generates OpenAPI docs and is fast to write. *Where it
appears:* the service `README.md`s, [`pyproject.toml`](../pyproject.toml).

### Frontend (Vite / React)

The optional **frontend** (`frontend/`) is a NASA-themed browser UI — including the
"add a source" onboarding wizard — built with **React** (a UI library) and **Vite** (a fast
dev server/bundler). *Where it appears:* `frontend/`, [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## ☁️ Azure managed twins (the real demo target)

> **Why this section exists — read this first.** This is an **enterprise proof-of-concept
> whose primary story is Azure**: "deploy to the cloud to show the full art of the
> possible." The local OSS stack above is the **dev/test loop**; the managed Azure services
> below are what you actually demo. Each local component maps to exactly one Azure twin.

### Azure (commercial / global vs Government)

**Azure** is Microsoft's public cloud. **Commercial (global) Azure** is the worldwide
default; **Azure Government** is a physically and logically isolated set of regions
(e.g. **US Gov Virginia**, **US Gov Arizona**) for US public-sector workloads with stricter
residency and personnel-access controls (see **ITAR/CUI**). *Where it appears:*
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md), [`infra/azure/`](../infra/azure/README.md).

### APIM — Azure API Management

**Azure API Management (APIM)** is Azure's **managed** API gateway — the cloud twin of
Kong. It adds a built-in **Developer Portal**, **products + subscriptions**, native Entra
integration, and an **AI gateway**, while enforcing the same JWT/rate-limit/correlation
policies. The repo ships an entire "APIM edition" alongside the Kong edition. *Where it
appears:* [`APIM-EDITION.md`](APIM-EDITION.md), [`APIM-CAPABILITIES.md`](APIM-CAPABILITIES.md),
[`infra/azure/modules/apim.bicep`](../infra/azure/modules/apim.bicep).

### APIM Developer Portal

The **Developer Portal** is APIM's managed, self-service website where consumers **browse**
APIs, read the OpenAPI, **try** calls live ("Try it" console), and **subscribe** for a key.
It is the managed twin of this repo's catalog UI + onboarding wizard. *Where it appears:*
[`APIM-EDITION.md`](APIM-EDITION.md).

### APIM products & subscriptions

In APIM a **product** bundles one or more APIs for consumers (e.g. "Artemis Data
Products"); a **subscription** is a consumer's grant to use a product, carrying a
**subscription key** they pass on each call. This is the managed analogue of the
"add a source" + per-consumer model in the OSS edition. *Where it appears:*
[`APIM-EDITION.md`](APIM-EDITION.md).

### APIM policy

An **APIM policy** is the XML rule set APIM runs per API/operation — the direct analogue of
Kong's plugin chain. Key policies used: `validate-azure-ad-token` (verify the Entra token),
`rate-limit-by-key` (per-subscription throttle), `set-header X-Correlation-ID`, and the
**AI-gateway** policies `llm-token-limit` / `llm-emit-token-metric` (cap and meter LLM token
usage). *Where it appears:* [`APIM-EDITION.md`](APIM-EDITION.md),
[`infra/azure/modules/apim.bicep`](../infra/azure/modules/apim.bicep).

### Microsoft Entra ID (formerly Azure AD)

**Microsoft Entra ID** is Azure's identity provider — it issues and validates the tokens
that prove who a caller is. It is the managed twin of the local identity issuer. On Azure,
APIM validates Entra tokens with `validate-azure-ad-token`. *In plain terms:* Entra is the
real "who are you?" service; the local issuer just fakes it for the laptop demo. *Where it
appears:* [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md), [`SECURITY.md`](SECURITY.md).

### ACA — Azure Container Apps

**Azure Container Apps (ACA)** is a managed service for running containers without managing
servers. In the live Azure deploy, **DAB** (and, in the Kong edition, Kong itself) run on
ACA with **internal ingress** — meaning only the gateway can reach DAB, not the public
internet. *Where it appears:* [`AZURE-LIVE-DEPLOYMENT.md`](AZURE-LIVE-DEPLOYMENT.md),
[`infra/azure/modules/containerapp-dab.bicep`](../infra/azure/modules/containerapp-dab.bicep).

### Azure Database for PostgreSQL — Flexible Server

The **managed PostgreSQL** offering on Azure (specifically the **Flexible Server**
deployment model). It replaces the local Postgres container as the system of record in the
cloud, with public access disabled. *Where it appears:*
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md),
[`infra/azure/modules/postgres.bicep`](../infra/azure/modules/postgres.bicep).

### Azure Monitor / Log Analytics / Application Insights

Azure's observability stack — the managed twin of Prometheus + Grafana. **Log Analytics** is
the workspace that **ingests** logs and metrics (Container Apps logs, APIM `GatewayLogs`);
**Application Insights** adds app-level tracing; **Azure Monitor** is the umbrella for
dashboards and alerts. *Where it appears:* [`SECURITY.md`](SECURITY.md),
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md),
[`infra/azure/modules/monitor.bicep`](../infra/azure/modules/monitor.bicep).

### Microsoft Sentinel

**Microsoft Sentinel** is Azure's cloud-native **SIEM** (Security Information and Event
Management — a system that collects security telemetry, runs detection rules, and manages
incidents). It is enabled on the Log Analytics workspace to give the demo a security
surface over the same gateway/app logs. *Where it appears:* [`SECURITY.md`](SECURITY.md).

### Microsoft Purview

**Microsoft Purview** is Azure's data-governance service: it **catalogs** data, applies
**classification** and **sensitivity labels**, and tracks **lineage** and data quality. It is
the managed twin of this repo's `data/classification.yml` "classify before exposure"
discipline. *Where it appears:* [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md),
[`SECURITY.md`](SECURITY.md).

### Azure Key Vault

**Azure Key Vault** is a managed secrets store. In the live deploy the database connection
string lives in Key Vault and the DAB Container App reads it at runtime via a **managed
identity** — the secret value is never baked into the app's config. *Where it appears:*
[`SECURITY.md`](SECURITY.md), [`AZURE-LIVE-DEPLOYMENT.md`](AZURE-LIVE-DEPLOYMENT.md).

### Managed identity

A **managed identity** is an Azure-managed credential attached to a resource (here, the DAB
Container App) so it can authenticate to other services (like Key Vault) **without any
stored secret**. *In plain terms:* the app proves who it is using an identity Azure issues
and rotates for it, so there is no password to leak. *Where it appears:*
[`SECURITY.md`](SECURITY.md).

### Dataverse

**Microsoft Dataverse** is a managed data platform (Power Platform) that exposes data as an
**OData v4** API with `$metadata` discovery. It is mentioned as an alternative managed way
to expose the SoR as an API (instead of DAB on Container Apps). *Where it appears:*
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

### Bicep

**Bicep** is Azure's domain-specific language for **Infrastructure as Code (IaC)** —
declarative files that define cloud resources to deploy. The repo's `infra/azure/` Bicep
**compiles** (`az bicep build`) but CI does not deploy it; it is reference material that maps
the local stack to managed services. *Where it appears:* [`infra/azure/`](../infra/azure/README.md),
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

### `.bicepparam`

A **Bicep parameters file** supplies values to a Bicep deployment. Here the Postgres admin
password is sourced from an environment variable via `readEnvironmentVariable` rather than
committed. *Where it appears:* [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md),
`infra/azure/main.bicepparam`.

### Azure CLI (`az`)

The **`az`** command-line tool drives Azure (login, deploy, query). *Where it appears:* the
deploy commands in [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md),
[`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md), `scripts/`.

### Resource group (RG)

A **resource group** is an Azure container that holds related resources (e.g.
`artemis-poc-rg`) and is deployed/torn down as a unit. *Where it appears:*
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md), `scripts/azure-teardown.sh`.

### Private endpoint / VNet

A **VNet (Virtual Network)** is a private network in Azure; a **private endpoint** gives a
service a private IP inside it with **no public path**. The reference `network.bicep` puts
the SoR behind a private endpoint — "true zero-move" in the cloud. *Where it appears:*
[`SECURITY.md`](SECURITY.md), [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md),
[`infra/azure/modules/network.bicep`](../infra/azure/modules/network.bicep).

### FedRAMP High

**FedRAMP (Federal Risk and Authorization Management Program)** is the US government's
standardized cloud-security authorization; **High** is its most stringent impact level.
Both commercial Azure and Azure Government hold FedRAMP High authorization. *Why this
matters:* it lets the project run the managed data platform in commercial Azure rather than
forcing the Government-region fallback. *Where it appears:*
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

### Microsoft Fabric / OneLake (explicitly **excluded**)

**Microsoft Fabric** is Microsoft's unified analytics SaaS, and **OneLake** is its built-in
data lake. They are **deliberately excluded** from this project because they are **not
available in Azure Government / GCC**. They appear only as a documented "excluded, and why"
note — a CI test (`tests/test_no_fabric.py`) enforces that the repo never recommends them.
*Where it appears:* [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md), `CLAUDE.md` hard
constraints.

### GCC (Government Community Cloud)

**GCC** is a Microsoft 365 / Azure environment for US government customers. It is named only
in the context of why Fabric/OneLake are excluded (not available there). *Where it appears:*
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

---

## 🪪 Identity, tokens & API security

> **Why this section exists:** the gateway's job is to let the *right* callers in and keep
> over-broad or anonymous calls out. These are the words for *how it knows who's calling*.

### OAuth2

**OAuth2** is the open standard for **authorization** — how a client obtains a token that
grants it scoped access to an API. This POC uses an OAuth2-style "get a token, present it on
each call" flow. *Where it appears:* [`SECURITY.md`](SECURITY.md), `CLAUDE.md` open-standards
constraint.

### OIDC — OpenID Connect

**OpenID Connect (OIDC)** is the **authentication** layer built on top of OAuth2 — it
standardizes *identity* (who the user is) and discovery endpoints like
`/.well-known/jwks.json`. The local issuer is described as an "OIDC/JWT issuer." *Where it
appears:* [`services/identity/README.md`](../services/identity/README.md),
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

### JWT — JSON Web Token

A **JWT (JSON Web Token, pronounced "jot")** is a compact, signed token carrying **claims**
(facts about the caller) that the gateway can verify without calling back to the issuer.
It's the **bearer token** consumers present. *In plain terms:* a tamper-evident ID badge —
the gateway checks the signature and expiry instead of phoning the issuer on every call.
*Where it appears:* everywhere; defined in [`SECURITY.md`](SECURITY.md),
[`services/identity/README.md`](../services/identity/README.md).

### Bearer token

A **bearer token** is a token that grants access simply by being presented ("the bearer"),
sent in the `Authorization: Bearer <token>` HTTP header. The JWTs minted here are bearer
tokens. *Where it appears:* [`SECURITY.md`](SECURITY.md), [`GRAPHQL.md`](GRAPHQL.md).

### Claim

A **claim** is one fact inside a JWT. The tokens here carry: `iss` (issuer), `aud`
(audience — who the token is for), `sub` (subject), `client_id` (which consumer —
**this is the one Kong meters by**), `iat`/`nbf`/`exp` (issued-at / not-before / expiry).
*Where it appears:* [`services/identity/README.md`](../services/identity/README.md),
[`SECURITY.md`](SECURITY.md).

### RS256

**RS256** is the signing algorithm: **RSA** asymmetric signature with **SHA-256** hashing.
The issuer signs tokens with a **private key**; the gateway verifies them with the matching
**public key** (so the gateway can validate without ever holding the secret). *Where it
appears:* [`SECURITY.md`](SECURITY.md), [`services/identity/README.md`](../services/identity/README.md).

### JWKS

**JWKS (JSON Web Key Set)** is the standard JSON document that publishes an issuer's
**public** signing keys, served at `/.well-known/jwks.json`. Kong (and APIM) fetch/render it
to know which keys to trust. *Where it appears:*
[`services/identity/README.md`](../services/identity/README.md), [`SECURITY.md`](SECURITY.md).

### `kid` (key ID)

The **`kid`** is a label identifying *which* key signed a token (here
`artemis-local-key-1`), so verifiers can pick the right public key from the JWKS. *Where it
appears:* [`services/identity/README.md`](../services/identity/README.md).

### PEM

**PEM** is a common text encoding for keys/certificates (Base64 between
`-----BEGIN…-----`/`-----END…-----` lines). The issuer can serve its public key as raw PEM
at `/public.pem` and accept a provided key via `JWT_PRIVATE_KEY_PEM`. *Where it appears:*
[`services/identity/README.md`](../services/identity/README.md), [`.env.example`](../.env.example).

### Consumer

A **consumer** is a registered caller identity the gateway meters and rate-limits by. This
demo has exactly two: **`analyst`** (the human/Python-client persona) and
**`artemis-agent`** (the MCP-agent persona). Kong maps a call to its consumer via the
token's `client_id` claim. *Where it appears:*
[`services/identity/README.md`](../services/identity/README.md), [`SECURITY.md`](SECURITY.md).

### Rate limiting / quota / metering

**Rate limiting** caps how many calls a consumer may make in a window (default **60/min**);
exceeding it returns **HTTP 429** with a `Retry-After` header. **Metering** is counting each
consumer's calls (for the dashboards and "who used what"). Together they enforce a **quota**
and curb runaway or bulk extraction. *Where it appears:* [`SECURITY.md`](SECURITY.md),
[`services/identity/README.md`](../services/identity/README.md).

### Correlation id

A **correlation id** is a unique identifier Kong stamps on every request (and returns to the
caller), so one call can be traced through gateway → API → logs end to end. The MCP tool and
demo answers surface it as proof the answer came *through* the gateway. *Where it appears:*
[`SECURITY.md`](SECURITY.md), [`services/mcp/README.md`](../services/mcp/README.md).

### Field-level redaction / column permissions

**Redaction** means withholding specific sensitive columns from a response. DAB applies
per-role **column permissions** (`fields.exclude`) so **Confidential** columns (unit cost,
net price/value) never leave the SoR for a marketplace consumer — the row still comes back,
just without those columns. *Why this matters:* the security control lives at the data API
(least privilege at the source), not bolted onto the gateway. *Where it appears:*
[`SECURITY.md`](SECURITY.md), [`services/dab/dab-config.json`](../services/dab/dab-config.json),
`tests/test_redaction.py`.

### Classification (Routine / Sensitive / Confidential)

**Classification** labels each field by sensitivity — here **Routine / Sensitive /
Confidential** — defined in `data/classification.yml` and applied to Postgres **at seed
time** (as column comments) and surfaced in the catalog. *Why this matters:* you classify
**before** the API is ever exposed, so confidential data is governed from day one (the
Purview discipline). *Where it appears:* [`SECURITY.md`](SECURITY.md), `data/classification.yml`.

### OWASP API Security Top 10

**OWASP (Open Worldwide Application Security Project)** publishes the **API Security Top
10** — the ten most critical API risks (2023 edition). [`SECURITY.md`](SECURITY.md) maps each
risk (API1…API10) to a concrete control in this POC (JWT auth, rate limiting, the over-broad
pull guard, etc.). *Where it appears:* [`SECURITY.md`](SECURITY.md).

### SIEM

**SIEM (Security Information and Event Management)** is a class of system that aggregates
security logs, runs detection analytics, and manages incidents. The Azure twin here is
**Microsoft Sentinel**. *Where it appears:* [`SECURITY.md`](SECURITY.md).

---

## 🗄️ Data & analytics platform (the lakehouse story)

> **Why this section exists:** once the data is a governed product, an **analytics**
> platform can be *just another governed consumer* — it reads the product through the
> gateway and builds reports, again without copying the source. These are the terms for that
> story.

### REST

**REST (Representational State Transfer)** is the common style for HTTP APIs: resources at
URLs, accessed with verbs like `GET`. DAB auto-generates a REST API (e.g.
`GET /api/SupplyRisk`). *Where it appears:* [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`GRAPHQL.md`](GRAPHQL.md).

### OData

**OData (Open Data Protocol)** is an open standard that adds query operators to REST URLs —
`$filter`, `$orderby`, `$first`/`$after` (paging), etc. — so a client can filter and sort on
the server. The MCP tool builds OData queries like
`?$filter=program eq 'Artemis-3' and avg_delay_days gt 30&$orderby=risk_score desc`.
*In plain terms:* a standard "query string grammar" for asking an API for exactly the slice
you want. *Where it appears:* [`services/mcp/README.md`](../services/mcp/README.md),
[`GRAPHQL.md`](GRAPHQL.md).

### `$metadata`

**`$metadata`** is OData's machine-readable schema document — it describes the available
entities and fields so consumers can discover the shape of the data without asking a human.
DAB exposes an equivalent discovery doc. *Where it appears:* [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

### GraphQL

**GraphQL** is an open query language for APIs where the *client* specifies exactly which
fields and nested shapes it wants in a single request. DAB auto-generates a GraphQL endpoint
alongside REST, and Kong governs it on the same `/graphql` route. *Why this matters:* one
auto-API, queryable as REST *or* GraphQL, both equally governed — the "multi-model" story.
*Where it appears:* [`GRAPHQL.md`](GRAPHQL.md).

### OpenAPI

**OpenAPI** is the open standard for **describing** a REST API in a machine-readable
document (endpoints, parameters, responses). DAB emits one; the catalog and APIM both publish
it so consumers can discover and "try" the API. *Where it appears:*
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`APIM-EDITION.md`](APIM-EDITION.md), the catalog.

### Azure Databricks

**Azure Databricks** is a managed **lakehouse** analytics platform on Azure (Apache
Spark–based). In the walkthrough it is **just another governed consumer**: it reads the data
product *through the gateway*, builds a medallion in Delta, and serves it for reporting.
*Where it appears:* [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md),
[`infra/azure/modules/databricks.bicep`](../infra/azure/modules/databricks.bicep).

### Lakehouse

A **lakehouse** combines a data **lake** (cheap storage of raw files) with a data
**warehouse** (structured, queryable tables) in one platform. Databricks is the lakehouse
here. *Where it appears:* [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md),
[`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md).

### Unity Catalog (UC)

**Unity Catalog (UC)** is Databricks' governance layer — a unified catalog of data assets
with permissions, lineage, and discovery, organised as `catalog.schema.table`. It is the
**managed** governance twin on Azure; **open-source Unity Catalog** is the fallback in Azure
Government. *Where it appears:* [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md),
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

### Delta Lake (Delta)

**Delta Lake** ("Delta") is the open table format Databricks writes — Parquet files plus a
transaction log giving ACID transactions, versioning, and schema enforcement on the lake.
The medallion tables are stored as Delta. *Where it appears:*
[`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md).

### Medallion (Bronze / Silver / Gold)

The **medallion architecture** is a layering convention for refining data: **Bronze** (raw
as-ingested) → **Silver** (cleaned/conformed) → **Gold** (curated, business-ready marts —
here `gold.artemis_supply_risk`). The notebook builds all three. *In plain terms:* raw →
tidy → ready-to-report. *Where it appears:* [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md).

### Databricks SQL (DBSQL) / SQL warehouse

**Databricks SQL** is the SQL query surface over the lakehouse; a **SQL warehouse** is the
compute that runs those queries (Serverless/Pro). Power BI connects to a SQL warehouse to
read the Gold mart. *Where it appears:* [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md),
`databricks/sql/dbsql_samples.sql`.

### Delta Sharing

**Delta Sharing** is an open protocol for sharing Delta tables with external consumers
**without copying** the data — they query the live table. It extends zero-move to analytics
sharing. *Where it appears:* [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md),
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

### ADLS Gen2 (HNS)

**Azure Data Lake Storage Gen2 (ADLS Gen2)** is Azure's data-lake storage; **HNS
(Hierarchical Namespace)** is the option that gives it real folders (needed by Databricks).
It is where the Delta files physically sit. *Where it appears:*
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md),
[`infra/azure/modules/databricks.bicep`](../infra/azure/modules/databricks.bicep).

### Azure Synapse

**Azure Synapse Analytics** is Azure's earlier analytics service, named as part of the
broader managed data-platform posture (alongside Databricks). *Where it appears:*
[`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

### Power BI (PBI)

**Power BI** is Microsoft's business-intelligence / reporting tool. It connects to the
Databricks SQL warehouse and builds the supply-risk report from the Gold mart — the final
"governed analytics" link in the chain. *Where it appears:*
[`POWERBI-GUIDE.md`](POWERBI-GUIDE.md), [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md).

### JDBC

**JDBC (Java Database Connectivity)** is a standard way for tools (like a Databricks
notebook in `postgres` mode) to connect directly to a relational database. *Note:* the
direct-JDBC path is the *privileged* read used for full-fidelity ETL; the **gateway** path is
the governed, zero-move read. *Where it appears:* [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md).

### Notebook

A **notebook** is an interactive document mixing code and prose cells (here a Databricks
`.ipynb`) that builds the medallion step by step. *Where it appears:*
`databricks/notebooks/01_zero_move_medallion.ipynb`,
[`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md).

### ETL

**ETL (Extract, Transform, Load)** is the general pattern of pulling data, reshaping it, and
landing it in a target — what the medallion notebook does. *Where it appears:*
[`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md).

---

## 📦 Procurement domain & dataset fields (SAP-shaped)

> **Why this section exists:** the synthetic dataset mimics an **SAP** procurement system,
> so it uses SAP's terse, German-rooted column names. This is the decoder ring. *Reminder:*
> every value is **synthetic** — vendor names even carry a `(SYNTHETIC)` suffix.

### SAP

**SAP** is the enterprise-software vendor whose ERP (Enterprise Resource Planning) system is
a common real-world system of record for procurement. The dataset is "SAP-shaped" — its
tables and field names imitate SAP's. *Where it appears:*
[`data/sample/artemis_procurement_DATA_DICTIONARY.md`](../data/sample/artemis_procurement_DATA_DICTIONARY.md).

### Artemis / Artemis-3

**Artemis** is the (real) NASA Moon-exploration program; **Artemis-3** is a mission within
it, used as the example program in the demo question. *(The procurement data about it is
entirely fabricated.)* *Where it appears:* throughout; the dataset and the supply-risk
question.

### Sole-source

A **sole-source** material is one available from only a single supplier — a key supply-chain
**risk** because there's no fallback if that vendor slips. The headline question filters for
sole-source parts. *Where it appears:*
[`data/sample/artemis_procurement_DATA_DICTIONARY.md`](../data/sample/artemis_procurement_DATA_DICTIONARY.md).

### Criticality (Critical / Essential / Routine)

**Criticality** ranks how mission-essential a material is — **Critical**, **Essential**, or
**Routine**. The demo question filters for `Critical`. *Where it appears:* the dataset, the
MCP tool's `criticality` argument.

### Pad anomaly

A **pad anomaly** flags a launch-pad shock event affecting an order — a synthetic
supply-disruption signal. *Where it appears:*
[`data/sample/artemis_procurement_DATA_DICTIONARY.md`](../data/sample/artemis_procurement_DATA_DICTIONARY.md).

### Risk score / risk tier

The **risk score** (0–100) is a derived per-material supply-chain risk; the **risk tier**
buckets it (**High ≥ 70**, **Medium ≥ 40**, **Low** below). The supply-risk view ranks by
score. *Where it appears:*
[`data/sample/artemis_procurement_DATA_DICTIONARY.md`](../data/sample/artemis_procurement_DATA_DICTIONARY.md),
[`GRAPHQL.md`](GRAPHQL.md).

### SAP field-name decoder

The dataset's columns use SAP's mnemonic names. The ones you'll meet:

| SAP field | Plain meaning |
|---|---|
| `LFA1` | SAP table: vendor master (suppliers) |
| `MARA` | SAP table: material master (parts) |
| `EKKO` / `EKPO` | SAP tables: purchase-order header / line item |
| `LIFNR` / `NAME1` | vendor number / vendor name |
| `CAGE_CODE` | Commercial And Government Entity code (a supplier identifier) |
| `MATNR` / `MAKTX` | material number / material description |
| `MATKL` | material group |
| `PROGRAM` | Artemis program a material belongs to |
| `CRITICALITY` | mission-criticality of the material |
| `STD_LEAD_TIME_DAYS` | standard procurement lead time |
| `EBELN` / `EBELP` | purchase-order number / line item |
| `BEDAT` / `EINDT` | PO date / promised delivery date |
| `ACTUAL_DELIVERY` / `DELAY_DAYS` | actual delivery date / slip in days |
| `MENGE` / `MEINS` | order quantity / unit of measure (UoM) |
| `NETPR` / `NETWR` / `WAERS` | unit (net) price / net value / currency — **Confidential, redacted** |
| `STD_UNIT_COST_USD` | standard unit cost — **Confidential, redacted** |
| `SOLE_SOURCE` / `PAD_ANOMALY` | single-supplier flag / launch-pad shock flag |
| `RISK_SCORE` / `RISK_TIER` | derived risk metrics (see above) |

> [!NOTE]
> `NETPR`, `NETWR`, and `STD_UNIT_COST_USD` are the columns DAB **redacts** for marketplace
> consumers (see [field-level redaction](#field-level-redaction--column-permissions)). The
> row still returns — only those cost/price columns are withheld.

*Where it appears:*
[`data/sample/artemis_procurement_DATA_DICTIONARY.md`](../data/sample/artemis_procurement_DATA_DICTIONARY.md),
[`SECURITY.md`](SECURITY.md).

---

## 🛠️ Project tooling & conventions

> **Why this section exists:** the words you'll see in the build, test, and CI plumbing.

### POC

**POC (Proof of Concept)** — a runnable demonstration that a pattern works, built to
persuade and to learn from, not a production system. This whole repo is one. *Where it
appears:* everywhere; the repo name.

### Make / Makefile (`make demo`)

**Make** runs named tasks defined in the [`Makefile`](../Makefile). `make demo` brings the
stack up healthy and prints the supply-risk answer; `make test` runs the test suite;
`make pricing` prints live Azure prices. *Where it appears:* [`Makefile`](../Makefile),
[`README.md`](../README.md).

### PRP

**PRP (here, the build spec — `PRP.md`)** is the self-contained specification the coding
agent follows: mission, architecture, phased plan, per-file contracts, hard constraints, and
Definition of Done. *Where it appears:* [`PRP.md`](../PRP.md), `CLAUDE.md`.

### Definition of Done (DoD)

The **Definition of Done** is the explicit checklist that says the POC is complete (stack up,
401/200/429 behaviours, zero-move proven, catalog + MCP working, live pricing, all docs,
CI green). *Where it appears:* `PRP.md` §13, `CLAUDE.md`.

### CI — Continuous Integration

**CI (Continuous Integration)** automatically runs lint and tests on every change (here via
**GitHub Actions** in `.github/workflows/`). "CI green" means all checks pass. *Where it
appears:* `.github/`, `CLAUDE.md`.

### ruff

**ruff** is the fast Python linter + formatter the project uses (`ruff format`, `ruff
check`) — code must be ruff-clean. *Where it appears:* [`pyproject.toml`](../pyproject.toml),
`.pre-commit-config.yaml`.

### pytest

**pytest** is the Python testing framework. The repo's tests include the constraint-proving
ones: `test_zero_move.py`, `test_no_fabric.py`, `test_redaction.py`. *Where it appears:*
[`tests/`](../tests/), [`pyproject.toml`](../pyproject.toml).

### pre-commit

**pre-commit** runs checks (formatting, secret detection via `detect-private-key`, etc.)
*before* a commit is recorded, catching issues early. *Where it appears:*
`.pre-commit-config.yaml`.

### healthcheck / `/healthz`

A **healthcheck** is a probe Docker (or Azure) uses to confirm a service is alive before
depending on it; most services expose a `GET /healthz` endpoint. Compose uses
`depends_on: condition: service_healthy` so services start in the right order. *Where it
appears:* [`docker-compose.yml`](../docker-compose.yml), the service READMEs.

### Compose profile (`core`)

A **Compose profile** lets you start a subset of services. The `core` profile is the
essential demo stack; the optional `frontend` profile adds the UI. *Where it appears:*
[`docker-compose.yml`](../docker-compose.yml), [`services/mcp/README.md`](../services/mcp/README.md).

### Azure Retail Prices API

The **Azure Retail Prices API** (`https://prices.azure.com/api/retail/prices`, public, no
auth) returns current list prices. `tools/azure_pricing.py` calls it so every quoted figure
is **live and dated** — never invented — and carries a source/date stamp. *Where it appears:*
`tools/azure_pricing.py`, `CLAUDE.md` hard constraints.

### Synthetic data

**Synthetic data** is fabricated, non-real data generated for the demo
(`data/synthetic_data.py`, `seed=42`). *Why this matters:* it is safe to share externally and
contains no **CUI/ITAR** content — the disclaimer banner must stay. *Where it appears:*
[`DISCLAIMER.md`](DISCLAIMER.md), `data/README.md`.

### CUI / ITAR / EAR

Three US data-sensitivity regimes that shape *where* data may run. **CUI (Controlled
Unclassified Information)** is sensitive-but-unclassified government info; **ITAR
(International Traffic in Arms Regulations)** and **EAR (Export Administration Regulations)**
control export/personnel access to defense and dual-use technology. They explain why strict
workloads land in Azure Government. *(All data here is synthetic and CUI/ITAR-free.)*
*Where it appears:* [`DISCLAIMER.md`](DISCLAIMER.md), [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

### Divestable

**Divestable** means the platform can be moved off a given vendor without a painful rebuild —
achieved here by using **open formats** (Delta Lake / Delta Sharing) and open-source-rooted
**Unity Catalog**. *Where it appears:* [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).

---

## 🔤 Quick acronym index

> One-line jogs to the full entry. Use the section links above for the full definition.

| Acronym | Expansion | Section |
|---|---|---|
| **ACA** | Azure Container Apps | [Azure twins](#-azure-managed-twins-the-real-demo-target) |
| **ADLS Gen2 / HNS** | Azure Data Lake Storage Gen2 / Hierarchical Namespace | [Data platform](#️-data--analytics-platform-the-lakehouse-story) |
| **APIM** | Azure API Management | [Azure twins](#-azure-managed-twins-the-real-demo-target) |
| **CI** | Continuous Integration | [Tooling](#️-project-tooling--conventions) |
| **CUI** | Controlled Unclassified Information | [Tooling](#️-project-tooling--conventions) |
| **DAB** | Data API Builder | [Local building blocks](#-local--open-source-building-blocks-the-dev-test-stack) |
| **DBSQL** | Databricks SQL | [Data platform](#️-data--analytics-platform-the-lakehouse-story) |
| **DoD** | Definition of Done | [Tooling](#️-project-tooling--conventions) |
| **EAR** | Export Administration Regulations | [Tooling](#️-project-tooling--conventions) |
| **Entra / Entra ID** | Microsoft Entra ID (formerly Azure AD) | [Azure twins](#-azure-managed-twins-the-real-demo-target) |
| **ETL** | Extract, Transform, Load | [Data platform](#️-data--analytics-platform-the-lakehouse-story) |
| **FedRAMP** | Federal Risk and Authorization Management Program | [Azure twins](#-azure-managed-twins-the-real-demo-target) |
| **GCC** | Government Community Cloud | [Azure twins](#-azure-managed-twins-the-real-demo-target) |
| **IaC** | Infrastructure as Code | [Azure twins](#-azure-managed-twins-the-real-demo-target) |
| **ITAR** | International Traffic in Arms Regulations | [Tooling](#️-project-tooling--conventions) |
| **JDBC** | Java Database Connectivity | [Data platform](#️-data--analytics-platform-the-lakehouse-story) |
| **JWKS** | JSON Web Key Set | [Identity & security](#-identity-tokens--api-security) |
| **JWT** | JSON Web Token | [Identity & security](#-identity-tokens--api-security) |
| **MCP** | Model Context Protocol | [Local building blocks](#-local--open-source-building-blocks-the-dev-test-stack) |
| **OData** | Open Data Protocol | [Data platform](#️-data--analytics-platform-the-lakehouse-story) |
| **OIDC** | OpenID Connect | [Identity & security](#-identity-tokens--api-security) |
| **OWASP** | Open Worldwide Application Security Project | [Identity & security](#-identity-tokens--api-security) |
| **PBI** | Power BI | [Data platform](#️-data--analytics-platform-the-lakehouse-story) |
| **PEM** | Privacy-Enhanced Mail (key/cert encoding) | [Identity & security](#-identity-tokens--api-security) |
| **PG** | PostgreSQL | [Local building blocks](#-local--open-source-building-blocks-the-dev-test-stack) |
| **POC** | Proof of Concept | [Tooling](#️-project-tooling--conventions) |
| **PRP** | the build spec (`PRP.md`) | [Tooling](#️-project-tooling--conventions) |
| **REST** | Representational State Transfer | [Data platform](#️-data--analytics-platform-the-lakehouse-story) |
| **RG** | Resource Group | [Azure twins](#-azure-managed-twins-the-real-demo-target) |
| **RS256** | RSA signature + SHA-256 | [Identity & security](#-identity-tokens--api-security) |
| **SAP** | the ERP vendor (SoR shape) | [Procurement domain](#-procurement-domain--dataset-fields-sap-shaped) |
| **SIEM** | Security Information and Event Management | [Identity & security](#-identity-tokens--api-security) |
| **SoR** | System of Record | [The core idea](#-the-core-idea) |
| **UC** | Unity Catalog | [Data platform](#️-data--analytics-platform-the-lakehouse-story) |
| **UoM** | Unit of Measure (`MEINS`) | [Procurement domain](#-procurement-domain--dataset-fields-sap-shaped) |
| **VNet** | Virtual Network | [Azure twins](#-azure-managed-twins-the-real-demo-target) |

---

## ➡️ Where to next

- New to the project? Read [`README.md`](../README.md), then
  [`ARCHITECTURE.md`](ARCHITECTURE.md) for how the pieces fit.
- Want the proof behind "zero-move"? [`ZERO-MOVE.md`](ZERO-MOVE.md).
- Security vocabulary in context? [`SECURITY.md`](SECURITY.md).
- The Azure (primary) story? [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md) and
  [`APIM-EDITION.md`](APIM-EDITION.md).
- The analytics chain? [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md) and
  [`POWERBI-GUIDE.md`](POWERBI-GUIDE.md).
- SAP field names? [`data/sample/artemis_procurement_DATA_DICTIONARY.md`](../data/sample/artemis_procurement_DATA_DICTIONARY.md).
