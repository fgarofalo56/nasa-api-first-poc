# 🔐 Security model

[Home](../README.md) > [Documentation](README.md) > **Security model**

> [!NOTE]
> **TL;DR** — Clients authenticate with short-lived **RS256 JWTs** from a local issuer
> (Entra ID stand-in). **Kong** validates every token at the edge, meters per consumer,
> and caps over-broad pulls; **Data API Builder** redacts Confidential columns at the
> source before the gateway ever sees them. Classification is applied *before* exposure
> and enforced as column permissions. The same shape maps to **Entra ID + APIM** on Azure.

> [!WARNING]
> All data and scenarios here are **synthetic** — see [`DISCLAIMER.md`](DISCLAIMER.md).
> This is an illustrative reference, not an official NASA document.

## 📚 Contents

- [🪪 Identity & token flow](#-identity--token-flow)
- [🛡️ OWASP API Security Top 10 (2023) — controls at the gateway](#️-owasp-api-security-top-10-2023--controls-at-the-gateway)
- [🏷️ Classify before exposure](#️-classify-before-exposure)
- [✂️ Field-level redaction (column permissions at the data API)](#️-field-level-redaction-column-permissions-at-the-data-api)
- [🔑 Secrets](#-secrets)
- [📊 Monitoring & SIEM (Azure)](#-monitoring--siem-azure)

## 🪪 Identity & token flow

OAuth2 bearer with **RS256 JWTs** from the local issuer (`services/identity`), which
stands in for **Microsoft Entra ID**:

1. A consumer POSTs to `/token` and receives a short-lived RS256 JWT
   (`iss`, `aud`, `sub`, `client_id`, `exp`). The issuer signs with a private key that
   is **generated at runtime and never committed** (persisted only in a Docker volume).
2. On startup the issuer publishes a **JWKS** (`/.well-known/jwks.json`) and renders its
   **public key into Kong's declarative config** — so the gateway validates exactly the
   tokens this issuer mints.
3. Kong's `jwt` plugin verifies the signature and `exp`, and maps the call to a consumer
   via the `client_id` claim (`analyst` / `artemis-agent`) for per-consumer metering.
4. A request with **no or an invalid token is rejected with 401 at the edge** — it never
   reaches DAB or Postgres.

```mermaid
sequenceDiagram
    autonumber
    participant C as Consumer<br/>(analyst / artemis-agent)
    participant I as Identity issuer<br/>(services/identity)
    participant K as Kong gateway
    participant D as Data API Builder
    participant P as Postgres (SoR)

    C->>I: POST /token (client credentials)
    I-->>C: short-lived RS256 JWT (iss, aud, sub, client_id, exp)
    Note over I,K: JWKS published; public key rendered into Kong config
    C->>K: API request + Bearer JWT
    alt no / invalid token
        K-->>C: 401 (never reaches DAB or Postgres)
    else valid token
        K->>K: jwt verify (sig + exp), map client_id → consumer, meter
        K->>D: forward request
        D->>P: read (column permissions applied per role)
        P-->>D: rows (Confidential columns excluded)
        D-->>K: response
        K-->>C: 200 + correlation id
    end
```

On Azure this becomes Entra ID + APIM's `validate-azure-ad-token` (see the Bicep policy
in [`infra/azure/modules/apim.bicep`](../infra/azure/modules/apim.bicep)).

## 🛡️ OWASP API Security Top 10 (2023) — controls at the gateway

| Risk | Control in this POC |
|---|---|
| **API1 Broken Object Level Auth** | DAB exposes read-only entities; no object mutation paths; sensitive fields classified (`classification.yml`). |
| **API2 Broken Authentication** | Kong `jwt` plugin validates RS256 signature + `exp`; unauthenticated → 401 at the edge. |
| **API3 Broken Object Property Auth** | Read-only `anonymous` role in DAB with **column permissions** (`fields.exclude`) that redact Confidential columns (unit cost, net price/value); no writes. |
| **API4 Unrestricted Resource Consumption** | `rate-limiting` (per-consumer, 60/min default, 429 + `Retry-After`) **and** the `pre-function` guard that blocks over-broad extraction (`$first > 200` → 400). |
| **API5 Broken Function Level Auth** | Only the explicit entity routes are published; everything else under the service is unrouted. |
| **API6 Unrestricted Access to Business Flows** | Per-consumer quota + metering; the OWASP guard caps bulk pulls. |
| **API8 Security Misconfiguration** | DB-less declarative Kong config (reviewable in `services/gateway/kong.yml`); SoR has no host ports; secrets via `.env`. |
| **API9 Improper Inventory Management** | The catalog publishes the contract, owner, classification, and request path — no shadow APIs. |
| **API10 Unsafe Consumption** | All access is the documented OpenAPI contract over TLS-terminable Kong; correlation id on every call for traceability. |

On Azure, APIM provides the managed equivalents — see
[Mitigate OWASP API threats with API Management](https://learn.microsoft.com/azure/api-management/mitigate-owasp-api-threats).

## 🏷️ Classify before exposure

`data/classification.yml` labels (Routine / Sensitive / Confidential) are applied to the
system of record as Postgres `COMMENT`s **at seed time** and surfaced in the catalog —
so confidential records (e.g. `purchase_orders.NETPR`) are governed and visible as such
*before* the API is ever called. This is the Microsoft Purview discipline, applied
locally.

## ✂️ Field-level redaction (column permissions at the data API)

Classification is **enforced**, not just labelled. Data API Builder applies per-role
**column permissions**, so the columns marked **Confidential** in `classification.yml`
never leave the system of record for a marketplace consumer:

| Entity | Confidential column redacted from the default consumer |
|---|---|
| `Material` | `std_unit_cost_usd` (unit cost) |
| `PurchaseOrder` | `netpr`, `netwr` (net price / net value) |

In [`services/dab/dab-config.json`](../services/dab/dab-config.json) the default
`anonymous` role reads with `fields.exclude` set to those columns; a privileged
`authenticated` role (an internal caller presenting the principal header) reads the full
record. The row is still returned — only the confidential **columns** are withheld — so
the headline supply-risk answer is unaffected while cost/price data is masked at the API
layer, before the gateway ever sees it. `tests/test_redaction.py` proves the confidential
fields are absent through Kong.

> [!NOTE]
> This is the robust, DAB-native equivalent of column-level masking in Microsoft Purview /
> Azure SQL. An earlier gateway-side body-rewrite approach was rejected — redaction belongs
> at the data API (least privilege at the source), not bolted onto the gateway response.

## 🔑 Secrets

| Context | How the secret is handled |
|---|---|
| **Local repo** | No secrets in the repo. Local config via `.env` (gitignored); the RS256 private key is generated at runtime into a volume and never committed (the `detect-private-key` pre-commit hook enforces this). |
| **Azure deploy params** | The PostgreSQL password is supplied via an env-sourced `.bicepparam` (`readEnvironmentVariable`), not source. |
| **Azure runtime** | The DB connection string lives in **Key Vault**. The DAB Container App reads it at runtime via a **system-assigned managed identity** + a Key Vault reference — the secret value is never inlined into the app's revision template. |

> [!IMPORTANT]
> In Azure the DB connection string is never inlined into the app's revision template —
> it is resolved from Key Vault via managed identity. See
> [`AZURE-LIVE-DEPLOYMENT.md`](AZURE-LIVE-DEPLOYMENT.md).

## 📊 Monitoring & SIEM (Azure)

- **Log Analytics** (`artemis-logs`) ingests Container Apps env logs and APIM
  `GatewayLogs` + metrics — the managed analogue of the local Prometheus/Grafana path.
- **Microsoft Sentinel** is enabled on that workspace (the deploy script onboards
  `Microsoft.SecurityInsights/onboardingStates/default`), giving the demo a SIEM surface:
  analytics rules, hunting, and incident workflows over the same gateway/app telemetry.
- **Network isolation (production hardening).** True zero-move in Azure puts the SoR behind
  a private endpoint with no public path — reference Bicep in
  [`infra/azure/modules/network.bicep`](../infra/azure/modules/network.bicep); see
  [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md).
