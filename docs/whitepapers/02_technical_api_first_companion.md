# API-First Interoperability and Governance

### Technical companion — Azure API Management, Dataverse, and Azure AI as the secure connective tissue

*Microsoft Federal — Data, Analytics & AI · Technical companion to the Executive Concept Paper · De-identified — cleared for external sharing*

---

## Abstract

A distributed mission enterprise is converging on a common target: an
**API-first, multi-model, zero-move-data ecosystem** spanning many centers and a
heterogeneous, multi-vendor estate. The defining requirement is no longer "which
AI platform wins," but "what makes a multi-vendor ecosystem interoperate securely,
govern uniformly, and scale without bulk data migration." This companion grounds
the architecture in five capabilities: **Azure API Management** as the enterprise
API gateway and AI gateway; the **Dataverse Web API** as an open OData v4 surface
with first-class schema discovery via `$metadata`; **Microsoft Graph** and **Azure
AI Foundry** as M365-data and model-hosting surfaces; agent surfaces governed
through the open **Model Context Protocol (MCP)**; and a single **Zero Trust** wrap
over the whole fabric. It closes with the compliance boundaries that govern
regulated workloads (FedRAMP High, Azure Government, GCC / GCC High / DoD), a
reference architecture, gateway sizing, and a worked zero-move use case. Every
technical assertion cites official Microsoft documentation; comparisons to
non-Microsoft products are generic and without benchmark claims. Microsoft Fabric
and OneLake are intentionally excluded — they are not available in Azure
Government / GCC — so the data platform is Azure Databricks (managed Unity Catalog,
Delta Lake, Delta Sharing) in commercial Azure at FedRAMP High, Azure Synapse, ADLS
Gen2, Azure SQL, and Data API Builder.

> **Companion accelerators.** This document pairs with a Microsoft API-first
> solution store of reference patterns and accelerators for the architecture below:
> https://fgarofalo56.github.io/csa-inabox/solution-store/

## 1. The multi-vendor AI ecosystem problem

A distributed mission enterprise rarely has the luxury — or the desire — of a
single AI vendor. Centers run different systems of record, procure models from
different providers for different tasks, and operate under data-residency and
export-control constraints that forbid casually relocating data. The resulting
architecture is, by design, multi-vendor and multi-model. That is a strength, not
a defect. But it surfaces a problem no individual model, assistant, or content
platform can solve on its own:

- **Interoperability** — heterogeneous backends must be reachable through
  consistent, discoverable interfaces.
- **Orchestration** — many models and agents must be selected, composed, and
  routed per use case.
- **Governance** — identity, authorization, rate, cost, residency, and audit must
  apply uniformly across vendors.

We frame the posture as five pillars and map Microsoft's role to each **as a
layer**, asserting the least-burden principle: work with how the enterprise exists
today.

| Pillar | Microsoft alignment (as the layer) |
|---|---|
| Multi-model | Azure AI Foundry's model catalog hosts first-party, partner, and community models that swap without application code changes. [16] |
| Distributed data | APIM facades backends where they already run; a self-hosted gateway executes next to the data in hybrid or multicloud locations. [9] |
| API-first mandate | APIM is a managed enterprise API gateway (gateway data plane + management plane + developer portal); Dataverse and Graph expose data over OData/REST. [1] |
| Zero-move data | The gateway brokers calls to data in place; no bulk migration is required to expose or govern a system of record. [9] |
| Interoperability | Open standards throughout — OData v4 (Dataverse, Graph), MCP (agents), OAuth 2.0/JWT (identity). [2][12] |

> **A candid scoping note.** The least-burden claim is strongest for *exposure and
> governance* — a gateway in front of systems that stay where they are. Where the
> enterprise chooses Microsoft-native enrichment (Dataverse as an enrichment store,
> Copilot Studio agents), that introduces Microsoft-managed surfaces, adopted
> deliberately per use case — not imposed by default. The architecture is additive,
> and each layer is independently adoptable.

> _Figure: Reference architecture — the shared backbone over data that stays in place — see docs/architecture.png._

## 2. Azure API Management as the enterprise gateway

Azure API Management (APIM) is Microsoft's fully managed enterprise API gateway,
composed of three planes: the **API gateway** (data plane), the **management
plane**, and the **developer portal**. [1] For a platform team writing vendor
requirements, the relevant capabilities are token/access management, rate limiting,
quota and chargeback, security-policy enforcement, multi-backend routing,
observability, hybrid deployment, and AI/LLM token-and-cost governance.

### 2.1 Token and access management
APIM subscriptions are named containers for a primary/secondary key pair; the
client presents the key in the `Ocp-Apim-Subscription-Key` header (default) or a
`subscription-key` query parameter, and a request without a valid key is rejected
at the gateway and never reaches the backend. Keys come in pairs for zero-downtime
rotation. **Tradeoff stated plainly:** APIM has no built-in subscription-key expiry
or automatic rotation — use OAuth 2.0 token-based auth for time-limited access, or
script rotation via PowerShell/SDK. [2]

### 2.2 Rate limiting, quota, and chargeback
APIM separates short-term burst protection from longer-term volume control:
`rate-limit` / `rate-limit-by-key` cap calls over a short window and return HTTP
429 with a `Retry-After` header; `quota` / `quota-by-key` enforce a renewable or
lifetime volume and return HTTP 403 when exhausted. Two operational facts matter
for a distributed deployment: rate-limit counters are maintained **per
gateway/region** (not globally synchronized), and `rate-limit-by-key` is not
available in the Consumption tier. For chargeback across centers, **products** are
APIM's top-level cost-tier mechanism — one product per cost tier, open or
protected, with auto- or admin-gated approval. [3][4][5]

### 2.3 Security-policy enforcement
APIM enforces request security through declarative policies scoped at global,
workspace, product, API, or operation level: `validate-jwt` (generic OIDC;
symmetric and asymmetric signatures; audience/issuer/required-claims checks),
`validate-azure-ad-token` (Entra-specific), `validate-client-certificate` (mTLS),
IP filtering, and managed-identity backend authentication. [4][6]

### 2.4 Multi-backend routing
APIM models backends as first-class entities and supports load-balanced pools of up
to 30 backends (round-robin, weighted, or priority distribution), optional session
affinity, and circuit breakers; `set-backend-service` redirects a call at runtime.
Balancing is approximate because gateways do not synchronize counters. [7][4]

### 2.5 Observability
Layered observability: Azure Monitor metrics (90-day retention); resource logs to
Log Analytics for KQL; Application Insights for end-to-end tracing and custom
metrics (via `emit-metric`); built-in Analytics; the API Inspector trace; Event
Hubs streaming; OpenTelemetry export from the self-hosted gateway; and Azure
Managed Grafana dashboards. [8]

### 2.6 Hybrid and self-hosted deployment — the zero-move enabler
The self-hosted gateway is a Linux Docker container pulled from the Microsoft
Artifact Registry and deployed to Kubernetes/AKS, Azure Arc, or Azure Container
Apps. It requires only **outbound TCP 443** to Azure for heartbeat, configuration
polling, and telemetry. Microsoft recommends pinning a specific image version tag
in production. This is the feature that makes zero-move real: the gateway runs
adjacent to an on-premises or other-cloud system of record and brokers calls
without relocating the data. [9]

### 2.7 The AI gateway — token, cost, and MCP governance
APIM's AI gateway is **not a separate product** — it extends the same gateway:
`llm-token-limit` (tokens-per-minute and/or token quota per counter key; 429 on
rate, 403 on quota; prompt-token pre-calculation), `llm-emit-token-metric`
(per-consumer token metrics to Application Insights for per-center cost
attribution), LLM semantic caching, and content safety; it supports OpenAI Chat
Completions/Responses and Anthropic Messages schemas (the Anthropic schema in v2
tiers). Crucially, APIM can **expose any managed REST API as a remote MCP server**
(operations become tools) and **proxy and govern existing external MCP servers**
(which must conform to MCP specification 2025-06-18+) — the same rate-limit, JWT,
IP-filter, and caching policies apply to MCP traffic. This is the mechanism for
token-exhaustion and cost control across multi-model orchestration, and it directly
addresses the cost trajectory of a token-broker approach. **Tradeoffs:**
REST-as-MCP exposes tools only (not resources or prompts), is not supported in
workspaces, and several capabilities carry preview-era constraints — re-verify
before architectural commitment. [9][10][11][12][13][14]

### 2.8 Azure API Management — capabilities for a federal API gateway
This is a single-column capability statement: every row is a documented,
cited Azure API Management capability against the dimensions that matter for a
federal API gateway. We make no characterization of any non-Microsoft product —
**the agency draws its own comparisons** against whatever alternatives it is
evaluating, using its own requirements and tests.

| Dimension | Azure API Management capability |
|---|---|
| Native cloud & identity | First-class Microsoft Entra integration (`validate-azure-ad-token`, managed-identity backend auth, RBAC); gateway data plane + management plane + developer portal delivered as one managed service. [1][6] |
| Zero-trust wrapping | OAuth 2.0 client↔gateway↔backend, JWT/Entra-token validation, mTLS client certificates, IP filtering, and managed identities — composed to the Microsoft Zero Trust API-protection guidance. [18] |
| Multi-backend / hybrid | Load-balanced backend pools (up to 30 backends, round-robin/weighted/priority, circuit breakers); a self-hosted Linux container deployable to Kubernetes/AKS, Azure Arc, or Azure Container Apps, requiring only outbound TCP 443. [7][9] |
| AI / LLM token & cost | The AI gateway extends the same gateway: `llm-token-limit`, `llm-emit-token-metric` for per-consumer cost attribution, LLM semantic caching, and content safety. [10][11] |
| Agent / MCP governance | Expose a managed REST API as a remote MCP server and proxy/govern existing external MCP servers (spec 2025-06-18+); the same rate-limit, JWT, IP-filter, and caching policies apply to MCP traffic. [12][13][14] |

### 2.9 Open-source gateway path — Kong self-hosted on AKS

Where divestability dominates, **Kong Gateway (OSS)** self-hosted on Azure
Kubernetes Service is the open-source path. It runs identically on-premises, on
AKS, or on any Kubernetes environment, with no cloud-vendor dependency.

**Topology.** Kong's recommended production topology is **hybrid mode** — a
control plane (CP) that manages configuration and serves the Admin API, and data
plane (DP) nodes that serve proxy traffic. Only the CP needs the database; DP nodes
pull the latest configuration from the CP (over port 8005) and cache it on local
disk, so DP nodes keep proxying — and can even be restarted — while the CP is down.
On Kubernetes, Kong's own guidance is hybrid mode without the ingress controller,
or DB-less mode with the Kong Ingress Controller, for most production scenarios. [51][52]

**Node sizing (Kong's published guidance).** Kong publishes data-plane sizing in
three tiers; the representative Azure VM is illustrative, not prescriptive:

| Tier | Config / throughput | CPU / RAM per DP node | Representative Azure VM |
|---|---|---|---|
| Small | < 1,000 entities, < 2,500 RPS, < 20 ms added latency | 1–2 cores / 2–4 GB | Standard A-series |
| Medium | < 10,000 entities, < 10,000 RPS, < 10 ms | 2–4 cores / 4–8 GB | General-purpose D/A-series |
| Large | 50,000+ entities, 10,000+ RPS | 8–16 cores / 16–32 GB | Compute-optimized F8s v2 |

Kong allocates roughly **500 MB of memory per worker process** (one worker per CPU
core by default) and recommends sizing the config cache (`mem_cache_size`)
accordingly — for example, 4–6 GB of cache on a 4-core / 8 GB node. Kong
explicitly discourages throttled/burstable instance types for large clusters. A
production-grade Kong data plane on AKS therefore starts with a small node pool of
non-burstable, general-purpose nodes (the validated `Standard_D8s_v5` Linux node
price appears in the platform pricing section), scaled horizontally behind the
cluster. Final sizing requires the agency's actual RPS, entity count, and latency
SLO. [53]

> **The operational trade-off, stated plainly.** Kong OSS is self-managed: the
> agency owns patching Kong and every plugin, monitoring CVE disclosures, planning
> upgrade windows, testing plugin compatibility, and maintaining HA through rolling
> upgrades. That burden is precisely why the program also evaluates a managed
> gateway — not a knock on Kong, but the honest decision factor. The two are not
> mutually exclusive: Kong can front on-premises legacy systems where divestability
> is paramount while a managed gateway handles cloud-native APIs in the same estate,
> under one catalog. [53]

## 3. Programmatic data access with the Dataverse Web API

This section answers the make-or-break questions for the API-first data strategy:
**how is Dataverse connected via a RESTful API, and how do you discover what is in
it?**

**Direct answer.** Dataverse exposes an OData v4.0 RESTful Web API at
`https://{organization}.api.crm.dynamics.com/api/data/v9.2/`. You discover the
complete schema by appending `$metadata` to that root, which returns the
authoritative CSDL (Conceptual Schema Definition Language) document describing
every entity, attribute, relationship, action, and function. [19][20]

### 3.1 Endpoint and service document
The endpoint follows `Protocol + Environment + Region + /api/data/ + Version +
Resource`. The current version is v9.2; it implements OData v4.0 (not 4.01) and is
JSON-only. A GET on the bare endpoint returns the **service document** — a JSON
list of every EntitySet name. [22][23]

### 3.2 Schema discovery via `$metadata`
Appending `$metadata` returns the CSDL "source of truth" — XML EDMX in the
`Microsoft.Dynamics.CRM` namespace (alias `mscrm`). **Names are case-sensitive:**
`accounts` resolves, `Account` returns 404; `name` resolves, `Name` returns 400.
Add `?annotations=true` for read-only/Computed/Permissions/Description detail; the
document is large (over 5 MB), so cache it. [19][24]

### 3.3 Required headers and query options
| Concern | Requirement |
|---|---|
| Required headers | `Accept: application/json`, `OData-MaxVersion: 4.0`, `OData-Version: 4.0`, `If-None-Match: null`; write bodies add `Content-Type: application/json`. `Prefer` enables `return=representation`, `odata.include-annotations`, `odata.maxpagesize`, `odata.track-changes`. [22] |
| Query options | `$select` (always set it), `$filter`, `$expand`, `$orderby`, `$apply`, `$top`, `$count` — all case-sensitive. `$skip`, `$search`, `$format` are not supported. Paging via `Prefer: odata.maxpagesize` + `@odata.nextLink`; default cap 5,000 rows (500 for elastic tables). [23] |

### 3.4 Querying schema as data
Beyond `$metadata`, the schema is queryable through metadata entity sets:
`EntityDefinitions`, `RelationshipDefinitions`, `GlobalOptionSetDefinitions`,
`ManagedPropertyDefinitions` — by alternate key (e.g.
`EntityDefinitions(LogicalName='account')`) or `MetadataId`. Type-specific
properties require casting (e.g.
`.../Attributes/Microsoft.Dynamics.CRM.PicklistAttributeMetadata`). [25][26][27]

### 3.5 Authentication
Dataverse accepts only OAuth 2.0 with Microsoft Entra ID; MSAL is the recommended
client. A delegated app needs the Dataverse `user_impersonation` scope and admin
consent. The scope pattern differs by client type: **public client** uses
`<environment-url>/user_impersonation`; **confidential client** uses
`<environment-url>/.default`. For a server-to-server caller with no interactive
user — the typical pattern for a notebook, pipeline, or agent — register an app,
add a client secret or X.509 certificate, and bind it to an **unlicensed
application user** assigned a least-privilege security role; S2S does not require
`user_impersonation`. [28][29][30]

### 3.6 Calling Dataverse from Python
Two supported paths: **(a)** the official `PowerPlatform-Dataverse-Client` SDK
(Python 3.10+, open source, wraps the Web API; authenticates with any
`azure-identity` `TokenCredential`); or **(b)** **direct Web API calls** — because
the surface is open OData v4, any HTTP client (`httpx`/`requests`) calls it after
acquiring an MSAL bearer token for the confidential-client scope
`https://{organization}.crm.dynamics.com/.default` and sending the required OData
headers. Service-protection limits return HTTP 429 with a 5-minute sliding-window
backoff; honor `Retry-After`. [31][32][33][21]

## 4. The cross-platform integration fabric and Zero Trust

The fabric is six interlocking surfaces under one Zero Trust wrap. Open standards
make it connective tissue, not a walled garden.

| Surface | What it provides |
|---|---|
| Azure API Management | The gateway and AI gateway: REST exposure, policy enforcement, token/cost governance, and MCP exposure/governance. [1][12] |
| Microsoft Graph API | A single endpoint, `https://graph.microsoft.com`, for people-centric M365 data — Calendar, Outlook/Exchange, OneDrive, OneNote, Teams, SharePoint, Planner. Copilot connectors bring external data inbound; Graph Data Connect provides opt-in bulk delivery (not required for routine access). [5] |
| Dataverse Web API | The OData v4 relational/enrichment surface with `$metadata` discovery (Section 3). [20][21] |
| Azure AI Foundry | PaaS model hosting and orchestration; the Agent Service supports prompt and hosted agents (containerized, with a dedicated Entra agent identity), built-in tools, on-behalf-of auth, and publishing to Teams / M365 Copilot. The catalog spans first-party and partner/community models; models swap without code change. [16][35][36] |
| Copilot Studio | Low-code agent authoring in the Power Platform; maker-built, admin-approved, Graph connectors for grounding. The pro-code alternative is the M365 Agents SDK. [38][39] |
| GitHub Copilot | An MCP host (agent mode connects to MCP servers), with enterprise/organization admin controls for managing Copilot policies, allow-listing MCP servers, and content exclusion. [65][66] (IDE-level controls: [40][41].) |

**The Zero Trust wrap.** Three principles — verify explicitly, least-privilege
access, assume breach — implemented consistently: at the platform level, Entra ID +
Conditional Access, RBAC + managed identities (no stored credentials), and network
segmentation; at the API layer, OAuth 2.0 client→gateway→backend, `validate-jwt` /
`validate-azure-ad-token`, mTLS client certificates, IP filtering, and the
`authentication-managed-identity` policy (injects a bearer token to backends, cached
until expiry). For Zero Trust APIs specifically, validate bearer *access* tokens
(not ID tokens), remove the default `User.Read` scope where unneeded, and block
legacy authentication. [17][18]

## 5. Making mission data AI-ready — the Purview remedy

The program's stated blocker is not access control; it is that mission data is
un-inventoried and inconsistently labeled, so a forward-deployed integration
effort cannot reliably tell what is truly sensitive from what is shareable. The
remedy is a catalog-and-quality discipline, and **Microsoft Purview is already
deployed at the agency** — a crawl of the estate has already run. The next step
is therefore not a new tool or a restart; it is to **operationalize that crawl**
into authoritative-source designations, a metadata standard, and a steward
workflow, with the catalog as the enforcement point. Purview's data-governance
work has five technical parts:

| Part | What Purview provides | Reference |
|---|---|---|
| **Profiling** | AI-assisted data profiling produces a column-level statistical snapshot (distribution, min/max, standard deviation, uniqueness, completeness, duplicates) so the actual state of a source is known before rules are written. | [67] |
| **Quality rules + scoring** | No-/low-code and AI-suggested rules across six dimensions (completeness, consistency, conformity, accuracy, freshness, uniqueness); each produces a score, aggregated to asset, data-product, and governance-domain levels — the measurable "is this data trustworthy yet" signal. | [68][69][70] |
| **Lineage** | The Unified Catalog traces relationships between data products and the assets behind them, so a quality issue can be tracked to its authoritative source and copies/derivations are visible. | [71][72] |
| **Unified catalog + classification + auto-labeling** | Governance domains, data products, glossary terms, and critical-data-elements organize the estate by business context; classification and auto-labeling policies apply sensitivity labels that **travel with the data** into the Data Map, SharePoint, SQL, and ADLS Gen2. | [71][73][64] |
| **Data-steward workflow** | Classification is human-in-the-loop: a data-quality steward (a Purview catalog role) reviews profiling output, authors/approves rules, resolves authoritative-source conflicts, and signs off before a data product is published — and the catalog records that workflow. | [68][74] |

> **Bootstrapping a catalog when existing labels are wrong.** Where prior labeling
> is incomplete or incorrect — the agency's actual situation — profiling plus
> rule-based scoring re-establishes a trustworthy baseline from the data itself,
> rather than trusting labels that were never applied to a standard. Auto-labeling
> then re-derives sensitivity from sensitive-information-types and trainable
> classifiers, with the steward confirming before publication. This is the step
> that unblocks everything downstream, including efforts elsewhere in the agency
> that are stalled precisely because the data was never inventoried to a standard.
> Operationalizing the existing crawl — not restarting it — is the move. [73][74]

## 5A. ATO and the sensitivity-label flow

Exposure must be governed before it is granted. The flow that keeps an API-first
program compliant:

1. **Classify and label at the source.** Microsoft Purview discovers and classifies
   data and applies sensitivity labels; labels travel with the data so confidential
   records are governed differently from routine ones — the program's core
   data-quality concern, addressed before exposure (Section 5). [64]
2. **Authorize the workload (ATO).** The workload runs inside an authorization
   boundary (FedRAMP High in global Azure, or Azure Government / GCC High for
   ITAR/CUI). The same APIM + Dataverse + OData/MCP patterns apply across
   boundaries; what changes is the cloud and the residency/personnel commitments
   (Section 7).
3. **Enforce at the gateway.** Identity (`validate-azure-ad-token`), least-privilege
   scopes, rate/quota, IP filtering, and content safety are applied at the gateway
   before any call reaches the backend.
4. **Audit continuously.** Azure Monitor / Log Analytics / Application Insights and
   Microsoft Sentinel ingest gateway, identity, and platform signals for continuous
   monitoring and incident response.

## 6. The software-assurance scanning pipeline (Track B link)

For the code asset class, the same standards-based posture applies. Consolidated
source control provides the inventory; **GitHub Advanced Security** provides code
scanning (the CodeQL engine), secret scanning with push protection, and dependency
review, with **Copilot Autofix** generating suggested fixes for CodeQL alerts;
**Microsoft Defender for Cloud** adds DevOps and code-to-cloud posture management
(CSPM/DevSecOps/CWPP) and **Defender for Containers** secures AKS and ACR images;
and **Microsoft Sentinel** ingests GitHub Advanced Security alerts and Azure
DevOps/Entra signals for SIEM/SOAR across the estate. [56][57][58][59]

The OWASP API Security Top 10 (2023) risks are enforced at the same gateway that
fronts the data — Microsoft publishes an explicit mapping of APIM policies to each
risk: `validate-jwt` / `validate-azure-ad-token` for broken authentication and
function-level authorization, `rate-limit(-by-key)` / `quota(-by-key)` /
`validate-content` for unrestricted resource consumption, `ip-filter` and
`validate-client-certificate` (mTLS) for access control, and the
`llm-content-safety` policy (with `shield-prompt`) for prompt-injection protection
on LLM traffic. [60][61] Supply-chain integrity follows the Microsoft Container
Secure Supply Chain pattern — generate an SPDX SBOM on every build, scan the
artifact, attach vulnerability reports and SBOMs as attestations, and sign images
(Notary Project `notation` + Azure Key Vault keys) — closing the loop from a
vulnerability to the API and mission that depend on it. [62][63] The full pipeline
is detailed in the Track B program; it rides the same identity, gateway, and
telemetry backbone as Track A.

## 7. Compliance in regulated and government clouds

The governing principle is decisive for a federal review chain: **data
classification drives the boundary; the architecture patterns do not change.** Both
global Azure and Azure Government hold FedRAMP High authorization; the practical
difference is data residency and personnel-access controls, not the FedRAMP level.

| Topic | Verified posture |
|---|---|
| FedRAMP High | Global Azure (all US public regions) and Azure Government (US Gov Arizona/Texas/Virginia) each hold a FedRAMP High P-ATO from the Joint Authorization Board, plus 400+ agency ATOs. Azure Government additionally carries DoD IL2/IL4/IL5 authorizations. [43][44] |
| The Azure Government delta | (a) physically isolated, US-only datacenters; (b) contractual US data residency; (c) operational access restricted to screened US persons. This matters for ITAR/EAR/export-controlled data. [43][45] |
| APIM in Azure Government | Generally available; documented feature gaps are narrow (Azure AD B2C not available; the Consumption tier is not offered in the US Government cloud). [45][46] |
| Dataverse / Power Platform | Delivered via GCC / GCC High / DoD (not under "Azure Government" branding). GCC uses public Entra ID; GCC High uses Microsoft Entra Government, targets DISA SRG IL4, and is the ITAR/DFARS option; DoD targets IL5. Customer content stays in the US. [44][47][48] |
| Azure OpenAI / AI Foundry in Gov | Gov-specific endpoints (`openai.azure.us`, AI Foundry at `ai.azure.us`); USGov DataZone routes inferencing across `usgovarizona`/`usgovvirginia` while keeping data at rest in the designated region; the model-and-region matrix is a trailing subset — verify before committing. [49][50] |
| Data platform | **Primary posture: Azure Databricks — with managed Unity Catalog, Databricks SQL, Delta Lake, and Delta Sharing — runs in commercial (global) Azure at FedRAMP High**, the boundary the agency has already accepted for Databricks. The managed-Unity-Catalog / Databricks-SQL gap applies **only to the Azure Government regions** (US Gov Arizona / US Gov Virginia, an ITAR subset), where the catalog would instead be open-source Unity Catalog on agency compute or Microsoft Purview. ADLS Gen2, Azure Synapse, and Azure SQL are available in both. [43][44][54][55] |

> **Candid architecture note — Unity Catalog by boundary.** For this program's
> primary boundary — **commercial (global) Azure at FedRAMP High**, which the agency
> has already accepted for Databricks — the **Databricks-managed Unity Catalog and
> Databricks SQL are available**, so the default catalog is managed Unity Catalog.
> The gap is **Gov-only**: in the Azure Government regions (an ITAR-bound subset)
> managed Unity Catalog and Databricks SQL are not currently available, so a
> Gov-region deployment would instead use the **open-source Unity Catalog** on
> agency-controlled compute or **Microsoft Purview** as the catalog/classification
> layer over ADLS Gen2 + Synapse + Azure SQL. Either way the catalog rests on the
> open-source-rooted Unity Catalog project (or open formats), so it remains
> divestable. Treat the managed-UC-in-Gov gap as an open item to re-verify against
> current Microsoft and Databricks documentation before any Gov-region commitment.
> Delta Lake and Delta Sharing remain open formats usable across the estate. [54][55]

**Posture statement.** Unclassified / CUI-adjacent → global Azure (FedRAMP High).
ITAR / strict-CUI / DoD → Azure Government + GCC High (and DoD where IL5 is
required). The same APIM + Dataverse Web API + OData/MCP patterns apply across
boundaries. [47][48]

## 8. Reference architecture and worked use case

The reference architecture (figure above) places the APIM self-hosted gateway
adjacent to each center's systems (outbound 443 only); the managed APIM service
provides the control plane; every call is OAuth-protected and policy-evaluated;
`llm-token-limit` and `llm-emit-token-metric` meter and cap agent token usage per
consumer; MCP exposure/governance brings agent clients under the same gateway
policies; and Microsoft Purview catalogs and classifies across the fabric. The
**Artemis supply-chain worked example** (separate companion) instantiates the
five-step zero-move pattern — expose, façade, catalog, consume — on synthetic SAP
procurement data.

> _Validated Azure pricing — generated live by `tools/azure_pricing.py` (Azure Retail Prices API)._

> **Staffing carries no dollar figures.** Azure infrastructure is priced above
> against live Azure list pricing; staffing and professional-services cost is a
> capability model (see the *Resourcing Framework*), not a dollar range.

## 9. The onboarding factory

The program's largest cost is not the gateway; it is building APIs on systems that
do not yet expose one and remediating the data quality that has to precede them.
The lever that collapses that cost is to make onboarding **repeatable** — a paved
path, not a series of bespoke integrations. We define the factory concretely so it
is inspectable rather than a slogan.

**Four stations, one assembly line.** Every source moves through the same four
stations in order; each station has a defined input, a defined output, and a clear
automated-vs-manual split.

| Station | What happens | Automated (IaC / template) | Manual (judgment) |
|---|---|---|---|
| **1 — Expose** | Stand up (or wrap) an API on the system of record. Where one exists, register it; where none exists, build a thin read API (or a Data API Builder layer over Azure SQL / a façade — Section 8). | Gateway onboarding (APIM/Kong config), Data API Builder config, IaC for the API host, baseline policies (JWT, rate-limit, quota, IP-filter). [83] | Building/refactoring the API on a legacy system that has none (the modernization cost driver). |
| **2 — Façade** | Project the source into a governed, relational/enrichment surface — the **Dataverse OData v4 Web API** — and attach M365 context via Graph where useful. | Dataverse entity templates; `$metadata`-driven client generation; Graph connector registration. | Modeling the entities and the enrichment joins for the specific source. |
| **3 — Catalog** | Publish the API and the data product: OpenAPI contract, owner, request path, classification, and lineage. | Auto-publish the OpenAPI spec to the API catalog; register the data product and run Purview profiling + quality scans. | The data-steward pass — authoritative-source designation, rule authoring, sensitivity sign-off (Section 5). |
| **4 — Consume** | Make the product usable by analysts and agents through the gateway, metered and audited, with the LLM gateway governing model traffic. | MCP exposure of the REST API; `llm-token-limit` / `llm-emit-token-metric`; per-consumer metering and audit wiring. | Defining per-consumer scopes and the access-approval policy for the product. |

**The paved-path checklist** — what "onboarded" means, identically, for every
source, so completion is objective:

1. API exists and is reachable, identity-validated, throttled, and metered at the gateway.
2. Schema is discoverable (`$metadata` / OpenAPI) and the contract is published to the catalog.
3. The data product is profiled, quality-scored, lineage-traced, and sensitivity-labeled, with a steward sign-off.
4. Access is request-able through a real owner, with least-privilege scopes enforced.
5. Telemetry and audit are flowing; model traffic (if any) is governed by the LLM gateway.

**A per-source runbook skeleton** (the repeatable unit of work):

```text
SOURCE: <system of record>            OWNER: <data owner>      TARGET TIER: <Gov/CUI/ITAR>
1. Discover  — locate the source, confirm owner, assess endpoint/quality/modernization (3-var score)
2. Expose    — register existing API OR build read API / Data API Builder layer; apply baseline policies
3. Façade    — project to Dataverse OData v4; add Graph/M365 context; verify $metadata
4. Govern    — Purview: register + scan, profile, author rules, score, classify, steward sign-off
5. Catalog   — publish OpenAPI + data product (owner, classification, lineage, request path)
6. Consume   — expose as MCP tool; wire llm-token-limit/metric; set scopes + access policy
7. Verify    — paved-path checklist 1–5 all green; record onboarding metrics
```

Because the factory standardizes stations 1, 3, and 4 as templates and IaC, the
incremental cost of each new source converges on the genuinely source-specific work
(station 2 modeling and the station-1 modernization where an API must be built). That
convergence is the program's principal cost lever — it is what moves a HIGH-band
source toward the LOW band in the per-source cost model (see the *Resourcing
Framework* scoring sheet).

## 10. Per-component divestability — the demonstrated exit

Lock-in avoidance is a hard requirement, so each component of the backbone has a
concrete, documented way out. Divestability is shown as a *technical exit*, not
asserted as a promise.

| Component | Exit path (how you leave) | Reference |
|---|---|---|
| **Dataverse (façade)** | Dataverse is an OData v4 service; every table is exportable through the standard **Web API** (`GET` with `$select`/`$filter`/`$expand`, paged via `@odata.nextLink`) by any standards-based OData/HTTP client — no proprietary client required. The schema itself exports as the CSDL `$metadata` document. | [20][23][75] |
| **APIM (gateway)** | An API governed by Azure API Management **exports as an OpenAPI definition** (`az apim api export --export-format OpenApiJsonFile|OpenApiYamlFile`, or the portal/PowerShell equivalents); the contract and operations port to the open-source Kong gateway, and policies are re-expressed as Kong plugins. APIM can also publish the API to Power Platform as a custom connector. | [76][77] |
| **Storage** | Data is stored in **Delta Lake** on open **ADLS Gen2** (open columnar format on Hadoop-compatible object storage) — readable by any Delta-capable engine, with no proprietary conversion to exit. | [78][79][80] |
| **Catalog / metadata** | The **managed Unity Catalog deployment is backed by an Apache-2.0 open-source project** — self-hostable on agency-controlled compute if the agency exits the managed service; metadata is not trapped. Open catalog alternatives (Apache-2.0-licensed) consume the same open formats, and **Delta Sharing** is an open cross-platform sharing protocol. | [54][55][82][81] |

This converts the divestability *claim* into a demonstrated *exit* per component —
the precise de-risking a lock-in-averse program requires before committing.

## Appendix — the data platform at FedRAMP High (commercial Azure), with the Government boundary noted

For this program, the zero-move data platform runs in **commercial (global) Azure at
FedRAMP High** — the boundary the agency has already accepted for Databricks. There,
the platform is **Azure Databricks with *managed* Unity Catalog, Databricks SQL, Delta
Lake, and Delta Sharing on ADLS Gen2,** plus Azure Synapse, Azure SQL, and Data API
Builder. **Data classification drives the boundary:** unclassified / CUI-adjacent
workloads run in commercial Azure (FedRAMP High); only an ITAR / strict-CUI **subset**
moves to Azure Government / GCC High — where managed Unity Catalog and Databricks SQL
are not yet available, so the catalog is open-source Unity Catalog on agency compute or
Microsoft Purview. Microsoft Fabric and OneLake remain intentionally excluded (not in
Azure Government / GCC). The pattern composes as follows:

- **Storage — Delta Lake on ADLS Gen2 (open format, in place).** Mission data lands
  (or stays) in **Delta Lake**, an open columnar format, on **ADLS Gen2** with the
  hierarchical namespace enabled. This is the open, queryable substrate; nothing is
  migrated to a proprietary store to be governed or consumed. [78][79][80]
- **Catalog + query — Azure Databricks with managed Unity Catalog (primary).** In
  commercial Azure at FedRAMP High, **managed Unity Catalog** governs the metadata and
  **Databricks SQL** queries Delta in place — both fully available at that boundary, so
  there is no need to self-host the catalog for the primary posture. Because the
  storage is the open Delta format, the engine remains the agency's choice (Databricks
  or any Delta-capable engine); the load-bearing fact is the open format. [43][44][80]
- **Government-subset exception.** For the ITAR-bound subset that runs in Azure
  Government, managed Unity Catalog and Databricks SQL are not currently available, so
  the catalog is the **open-source Unity Catalog** on agency-controlled compute, or
  **Microsoft Purview** over ADLS Gen2 + Synapse + Azure SQL (Azure Databricks itself
  is available in US Gov Arizona / US Gov Virginia). Delta Lake and Delta Sharing
  remain open formats across both boundaries. [54][55]
- **Relational façade — Azure SQL + Data API Builder.** Where a relational source or
  enrichment store is needed, **Data API Builder** generates REST and GraphQL
  endpoints over Azure SQL (and other databases) so the data becomes API-first
  without bespoke service code — a façade the gateway then governs. [83]
- **Gateway + façade placement.** The **APIM self-hosted gateway** (or Kong on AKS)
  runs *next to* this platform (outbound-443-only), brokering identity-validated,
  metered calls to data that stays in ADLS Gen2 / Azure SQL; the **Dataverse OData v4
  Web API** provides the governed relational/enrichment façade and M365 context
  (Section 3). No bulk migration is required to expose or govern any of it. [9][20]

> **Posture, restated.** The primary data platform is **Azure Databricks (managed
> Unity Catalog + Databricks SQL + Delta Lake + Delta Sharing) in commercial Azure at
> FedRAMP High**, with Azure Synapse, ADLS Gen2, Azure SQL, and Data API Builder, and
> Microsoft Purview for classification. The managed-UC / Databricks-SQL gap applies
> **only** to the Azure Government regions (the ITAR subset), where open-source Unity
> Catalog or Purview provides the catalog — an open item to re-verify against current
> Microsoft and Databricks documentation before any Gov-region commitment. [43][44][54][55]

## References

All sources are official Microsoft documentation; URLs were verified during
research. Comparisons to non-Microsoft products are generic, without benchmark
claims, except where a product is named in a migration or interoperability context.

1. What is Azure API Management?  https://learn.microsoft.com/azure/api-management/api-management-key-concepts
2. Subscriptions in Azure API Management  https://learn.microsoft.com/azure/api-management/api-management-subscriptions
3. Advanced request throttling with Azure API Management  https://learn.microsoft.com/azure/api-management/api-management-sample-flexible-throttling
4. API Management policy reference  https://learn.microsoft.com/azure/api-management/api-management-policies
5. Overview of Microsoft Graph  https://learn.microsoft.com/graph/overview
6. Validate JWT policy  https://learn.microsoft.com/azure/api-management/validate-jwt-policy
7. Backends in API Management  https://learn.microsoft.com/azure/api-management/backends
8. Observability in Azure API Management  https://learn.microsoft.com/azure/api-management/observability
9. Self-hosted gateway overview  https://learn.microsoft.com/azure/api-management/self-hosted-gateway-overview
10. Limit large language model API token usage  https://learn.microsoft.com/azure/api-management/llm-token-limit-policy
11. AI gateway capabilities in Azure API Management  https://learn.microsoft.com/azure/api-management/genai-gateway-capabilities
12. About MCP servers in Azure API Management  https://learn.microsoft.com/azure/api-management/mcp-server-overview
13. Expose a REST API in API Management as an MCP server  https://learn.microsoft.com/azure/api-management/export-rest-mcp-server
14. Expose and govern an existing MCP server  https://learn.microsoft.com/azure/api-management/expose-existing-mcp-server
16. Microsoft Foundry Models overview  https://learn.microsoft.com/azure/ai-foundry/concepts/foundry-models-overview
17. Authentication and authorization to APIs in Azure API Management  https://learn.microsoft.com/azure/api-management/authentication-authorization-overview
18. API protection (Zero Trust for developers)  https://learn.microsoft.com/security/zero-trust/develop/protect-api
19. Web API service documents  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/web-api-service-documents
20. Use the Microsoft Dataverse Web API (overview)  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/overview
21. Web API types and operations (Dataverse)  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/web-api-types-operations
22. Compose HTTP requests and handle errors  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/compose-http-requests-handle-errors
23. Use OData to query data  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/query/overview
24. Troubleshoot Dataverse Web API client errors  https://learn.microsoft.com/troubleshoot/power-platform/dataverse/dataverse-web-api-and-sdk/web-api-client-errors
25. Use the Web API with table definitions  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/use-web-api-metadata
26. Query table definitions using the Web API  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/query-metadata-web-api
27. Retrieve table definitions by name or MetadataId  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/retrieve-metadata-name-metadataid
28. Use OAuth authentication with Microsoft Dataverse  https://learn.microsoft.com/power-apps/developer/data-platform/authenticate-oauth
29. Tutorial: Register an app with Microsoft Entra ID  https://learn.microsoft.com/power-apps/developer/data-platform/walkthrough-register-app-azure-active-directory
30. Build web applications using server-to-server (S2S) authentication  https://learn.microsoft.com/power-apps/developer/data-platform/build-web-applications-server-server-s2s-authentication
31. Getting started — Dataverse SDK for Python  https://learn.microsoft.com/power-apps/developer/data-platform/sdk-python/get-started
32. Dataverse SDK for Python overview  https://learn.microsoft.com/power-apps/developer/data-platform/sdk-python/overview
33. Authenticate to Microsoft Dataverse with the Web API  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/authenticate-web-api
35. What is Microsoft Foundry Agent Service?  https://learn.microsoft.com/azure/ai-foundry/agents/overview
36. What are hosted agents?  https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents
38. Set up Agent Store in Microsoft 365 Copilot  https://learn.microsoft.com/microsoft-365/copilot/copilot-agent-store
39. Extend Microsoft 365 Copilot with agents  https://learn.microsoft.com/microsoft-copilot-studio/microsoft-copilot-extend-copilot-extensions
40. Use built-in and custom agents with GitHub Copilot (Visual Studio)  https://learn.microsoft.com/visualstudio/ide/copilot-specialized-agents
41. Admin controls for GitHub Copilot  https://learn.microsoft.com/visualstudio/ide/visual-studio-github-copilot-admin
43. Azure, Dynamics 365, Microsoft 365, and Power Platform services compliance scope  https://learn.microsoft.com/azure/azure-government/compliance/azure-services-in-fedramp-auditscope
44. Federal Risk and Authorization Management Program (FedRAMP)  https://learn.microsoft.com/azure/compliance/offerings/offering-fedramp
45. Compare Azure Government and global Azure  https://learn.microsoft.com/azure/azure-government/compare-azure-government-global-azure
46. Feature-based comparison of the Azure API Management tiers  https://learn.microsoft.com/azure/api-management/api-management-features
47. Dynamics 365 US Government (GCC / GCC High / DoD)  https://learn.microsoft.com/power-platform/admin/microsoft-dynamics-365-government
48. Power Automate US Government  https://learn.microsoft.com/power-automate/us-govt
49. Azure OpenAI in Azure Government  https://learn.microsoft.com/azure/ai-foundry/openai/azure-government
50. What is Azure Government?  https://learn.microsoft.com/azure/azure-government/documentation-government-welcome
51. Kong Gateway Hybrid Mode  https://developer.konghq.com/gateway/hybrid-mode/
52. Kong Ingress Controller (Kubernetes) documentation  https://docs.konghq.com/kubernetes-ingress-controller/latest/
53. Kong Gateway resource sizing guidelines  https://developer.konghq.com/gateway/resource-sizing-guidelines/
54. Features with limited regional availability (Azure Databricks — Unity Catalog / Databricks SQL not in Azure Government)  https://learn.microsoft.com/azure/databricks/resources/feature-region-support
55. Azure Databricks supported regions  https://learn.microsoft.com/azure/databricks/resources/supported-regions
56. Set up code scanning — GitHub Advanced Security  https://learn.microsoft.com/azure/devops/repos/security/github-advanced-security-code-scanning
57. Copilot Autofix for code scanning  https://learn.microsoft.com/azure/devops/repos/security/github-advanced-security-code-scanning-autofix
58. Overview of Microsoft Defender for Cloud DevOps security  https://learn.microsoft.com/azure/defender-for-cloud/defender-for-devops-introduction
59. Defender for Containers deployment overview  https://learn.microsoft.com/azure/defender-for-cloud/defender-for-containers-deployment-overview
60. Recommendations to mitigate OWASP API Security Top 10 threats using API Management  https://learn.microsoft.com/azure/api-management/mitigate-owasp-api-threats
61. Enforce content safety checks on LLM requests (llm-content-safety policy)  https://learn.microsoft.com/azure/api-management/llm-content-safety-policy
62. Overview of the Build stage — Container Secure Supply Chain  https://learn.microsoft.com/azure/security/container-secure-supply-chain/articles/container-secure-supply-chain-implementation/build-overview
63. Adopt updates for open-source software (SBOM generation)  https://learn.microsoft.com/security/zero-trust/prioritizing-defense/adopt-open-source-updates
64. Microsoft Purview Information Protection  https://learn.microsoft.com/purview/information-protection
65. Managing policies and features for Copilot in your organization  https://docs.github.com/en/copilot/managing-copilot/managing-github-copilot-in-your-organization/managing-policies-and-features-for-copilot-in-your-organization
66. Configuring content exclusions for GitHub Copilot  https://docs.github.com/en/copilot/managing-copilot/configuring-content-exclusions-for-github-copilot
67. Configure and run data profiling for a data asset (Microsoft Purview)  https://learn.microsoft.com/purview/unified-catalog-data-quality-profiling
68. Create data quality rules (Microsoft Purview Unified Catalog)  https://learn.microsoft.com/purview/unified-catalog-data-quality-rules
69. Overview of data quality in Microsoft Purview Unified Catalog  https://learn.microsoft.com/purview/unified-catalog-data-quality
70. Review data quality scores of data assets  https://learn.microsoft.com/purview/unified-catalog-data-quality-scores
71. Learn about Microsoft Purview Unified Catalog (catalog, lineage, governance domains)  https://learn.microsoft.com/purview/unified-catalog
72. Data governance with Microsoft Purview (lineage and data confidence)  https://learn.microsoft.com/purview/data-governance-overview
73. Learn about sensitivity labels in Data Map — labels travel with the data; auto-labeling  https://learn.microsoft.com/purview/data-map-sensitivity-labels
74. Microsoft Purview data governance roles and permissions (data-quality steward)  https://learn.microsoft.com/purview/data-governance-roles-permissions
75. Retrieve a table row using the Dataverse Web API (OData export)  https://learn.microsoft.com/power-apps/developer/data-platform/webapi/retrieve-entity-using-web-api
76. az apim api — Azure CLI reference (includes `api export` to OpenAPI)  https://learn.microsoft.com/cli/azure/apim/api
77. Export APIs from Azure API Management to Microsoft Power Platform (custom connector)  https://learn.microsoft.com/azure/api-management/export-api-power-platform
78. Introduction to Azure Data Lake Storage  https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-introduction
79. Azure Data Lake Storage hierarchical namespace  https://learn.microsoft.com/azure/storage/blobs/data-lake-storage-namespace
80. What is Delta Lake? (open storage format)  https://learn.microsoft.com/azure/databricks/delta/
81. What is OpenSharing? (Delta Sharing — open protocol)  https://learn.microsoft.com/azure/databricks/delta-sharing/
82. Unity Catalog open-source project (Apache-2.0)  https://unitycatalog.io
83. What is Data API builder for Azure Databases? (REST/GraphQL over Azure SQL)  https://learn.microsoft.com/azure/data-api-builder/overview

*Competitor-anonymized and cleared for external sharing — discloses no sensitive
internals and names no competitor. All technical
assertions cite official Microsoft sources. Microsoft Fabric and OneLake are
intentionally excluded (not in Azure Government / GCC). The primary data platform is
**Azure Databricks with managed Unity Catalog, Databricks SQL, Delta Lake, and Delta
Sharing, in commercial (global) Azure at FedRAMP High** — the boundary the agency has
already accepted for Databricks — plus Azure Synapse, ADLS Gen2, Azure SQL, and Data
API Builder. The managed-Unity-Catalog / Databricks-SQL gap applies only to the Azure
Government regions (an ITAR subset), where open-source Unity Catalog or Microsoft
Purview provides the catalog.*
