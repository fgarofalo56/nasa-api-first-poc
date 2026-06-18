# What Azure API Management adds over the OSS gateway

> Framing (per repo constraints): **Kong OSS is the path we *built*** in this POC; **Azure
> API Management (APIM) is the managed Azure equivalent** the whitepapers point to. This
> doc is the "what does the managed gateway add?" answer for a customer conversation — no
> third-party competitors are compared.

The POC's Kong (DB-less) already does JWT validation, rate-limiting, per-consumer metering,
correlation IDs, CORS, and an OWASP guard. APIM does all of that **and** adds managed
capabilities that are relevant to this program:

| Capability | OSS Kong (built here) | **APIM (managed) adds** | Why it matters here |
|---|---|---|---|
| **Developer Portal** | — (our catalog UI is the analogue) | Built-in, customizable **self-service portal**: browse APIs, read docs, **try-it console**, sign up for keys | The managed version of our marketplace/catalog — self-service discovery without tribal knowledge |
| **Products & Subscriptions** | per-consumer JWT creds | Package APIs into **products**, self-service **subscription keys**, per-product quotas/terms | Onboarding consumers + tiered access governance |
| **Identity** | local RS256 issuer | Native **Microsoft Entra ID** (`validate-azure-ad-token`), managed identity, OAuth2 | Tenant-grade auth with no key handling |
| **AI / GenAI gateway** | — | `llm-token-limit`, `llm-emit-token-metric`, **semantic caching**, LLM request logging | The "AI as connective tissue" story — govern + meter LLM/agent traffic the same way |
| **Self-hosted gateway** | (Kong can self-host) | **Managed control plane + self-hosted data plane** on-prem / other clouds / Gov | Keep data in-place for residency (ITAR/CUI) while centrally governed — the zero-move enabler |
| **Policy engine** | Lua plugins | Rich **XML policy** pipeline: transform, cache, validate-content, mock, rewrite | OWASP API Top-10 mitigations as first-class policies |
| **Observability** | Prometheus/Grafana | Native **Azure Monitor / App Insights**, request tracing, analytics | Enterprise telemetry without standing up your own stack |
| **Versioning** | route config | **API versions + revisions**, named values, certificate mgmt | Safe API evolution at scale |
| **Operations** | self-managed | Managed scaling, multi-region, SLA, VNet integration | Run-by-Azure, FedRAMP-authorized |

## What I'd show a customer (in priority order)

1. **Developer Portal** — the highest-impact visual; it's the managed twin of our catalog +
   "add a source" story (self-service discovery + try-it + subscriptions).
2. **AI gateway policies** (`llm-token-limit` / `llm-emit-token-metric`) — ties the
   marketplace to the agent/LLM governance narrative.
3. **Self-hosted gateway** — the residency/zero-move enabler for Gov/ITAR boundaries.
4. **Products/subscriptions + Entra** — consumer onboarding and tenant-grade identity.

## The honest mapping (so the demo is credible)

- Everything the POC's Kong does has a 1:1 APIM policy (see `infra/azure/modules/apim.bicep`:
  `validate-azure-ad-token` + `rate-limit-by-key` + correlation header).
- The POC's **catalog UI + onboarding wizard** are the open-source analogue of APIM's
  **Developer Portal + product onboarding** — same idea, managed vs. self-hosted.
- The POC's **Prometheus/Grafana** is the analogue of **Azure Monitor**.

## Want it live?

A live APIM instance (Developer tier) can front the deployed DAB API and light up the
**Developer Portal** for a real click-through. Provisioning APIM Developer takes ~30–45 min
and carries monthly cost, so it's an opt-in add to the demo (the reference policy is already
in `infra/azure/modules/apim.bicep`). Ask and I'll deploy it.
