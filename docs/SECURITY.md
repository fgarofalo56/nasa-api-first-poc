# Security model

## Identity & token flow

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

On Azure this becomes Entra ID + APIM's `validate-azure-ad-token` (see the Bicep policy
in `infra/azure/modules/apim.bicep`).

## OWASP API Security Top 10 (2023) — controls at the gateway

| Risk | Control in this POC |
|---|---|
| **API1 Broken Object Level Auth** | DAB exposes read-only entities; no object mutation paths; sensitive fields classified (`classification.yml`). |
| **API2 Broken Authentication** | Kong `jwt` plugin validates RS256 signature + `exp`; unauthenticated → 401 at the edge. |
| **API3 Broken Object Property Auth** | Read-only `anonymous` role in DAB; OData `$select` is the only projection; no writes. |
| **API4 Unrestricted Resource Consumption** | `rate-limiting` (per-consumer 60/min, 429 + `Retry-After`) **and** the `pre-function` guard that blocks over-broad extraction (`$first > 200` → 400). |
| **API5 Broken Function Level Auth** | Only the explicit entity routes are published; everything else under the service is unrouted. |
| **API6 Unrestricted Access to Business Flows** | Per-consumer quota + metering; the OWASP guard caps bulk pulls. |
| **API8 Security Misconfiguration** | DB-less declarative Kong config (reviewable in `kong.yml`); SoR has no host ports; secrets via `.env`. |
| **API9 Improper Inventory Management** | The catalog publishes the contract, owner, classification, and request path — no shadow APIs. |
| **API10 Unsafe Consumption** | All access is the documented OpenAPI contract over TLS-terminable Kong; correlation id on every call for traceability. |

On Azure, APIM provides the managed equivalents — see
[Mitigate OWASP API threats with API Management](https://learn.microsoft.com/azure/api-management/mitigate-owasp-api-threats).

## Classify before exposure

`data/classification.yml` labels (Routine / Sensitive / Confidential) are applied to the
system of record as Postgres `COMMENT`s **at seed time** and surfaced in the catalog —
so confidential records (e.g. `purchase_orders.NETPR`) are governed and visible as such
*before* the API is ever called. This is the Microsoft Purview discipline, applied
locally.

## Secrets

- No secrets in the repo. Local config via `.env` (gitignored); the RS256 private key is
  generated at runtime into a volume and never committed (the `detect-private-key`
  pre-commit hook enforces this).
- Azure deployment supplies the PostgreSQL password via an env-sourced `.bicepparam`
  (`readEnvironmentVariable`), not source.
