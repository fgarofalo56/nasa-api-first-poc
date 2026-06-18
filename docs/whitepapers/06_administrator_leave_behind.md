# API-First, in One Page

### An API-first approach for the mission enterprise — administrator brief

*An illustrative NASA-mission use case — API-First Data Marketplace (reference architecture).*

> ⚠️ **Illustrative reference · sample data only · not an official NASA document.**
> This paper presents a **generic** API-first, zero-move data-marketplace use case for a
> mission enterprise. It is an educational architecture illustration — **not** affiliated
> with, endorsed by, or approved by NASA, and not a proposal, commitment, or statement of
> work. All names, vendors, prices, quantities, dates, and scenarios are **synthetic and
> fabricated**; **no real NASA, ITAR, CUI, or procurement-sensitive data** is included.
> Product and architecture choices are examples — verify against current vendor docs.
> Provided "as is," without warranty. See [`../DISCLAIMER.md`](../DISCLAIMER.md).

---

## 📑 Table of Contents

- [The decision in front of you](#-the-decision-in-front-of-you)
- [What you are actually solving](#-what-you-are-actually-solving)
- [Two arguments no alternative can rebut](#-two-arguments-no-alternative-can-rebut)
- [What we recommend](#-what-we-recommend)
- [What we ask](#-what-we-ask)

---

## 📋 The decision in front of you

The agency is mandating that mission data be exposed through governed APIs,
discoverable in an enterprise catalog, with access controls — an enterprise
entitlement led by the OCIO. The question is not "which AI." It is **how to make a
multi-vendor, multi-model, zero-move ecosystem interoperate securely and uniformly,
without moving the data.** Microsoft's answer is to be the **connective tissue** —
the secure interoperability, orchestration, and governance layer — on open
standards, not a walled garden.

## 🎯 What you are actually solving

The blocker is not access control. It is that mission data is **un-inventoried and
inconsistently labeled**, and decades of in-house code are **un-scanned**. So the
program leads with **making the data AI-ready** — inventory and classify before you
expose anything — and with **software assurance**, not with a gateway purchase. One
platform governs three asset classes: **data, APIs, and code.**

## 🔒 Two arguments no alternative can rebut

- **Identity is already Microsoft Entra ID.** The token validation under the
  gateway, the per-org metering on model usage, the agents that consume APIs, and
  the zero-trust wrap all ride the identity the agency already runs. The
  least-burden claim is real, not aspirational.
- **The agency already owns the API surfaces** the mandate will require it to
  expose — Dataverse, GitHub, SharePoint, Microsoft 365 Graph. Nothing to acquire;
  just turn them on as governed APIs.

> **We do not need to win the gateway.** The gateway can be open-source and
> divestable. We win on the identity already in place, the surfaces the agency
> already owns, the model economics at the gateway, and the code-assurance layer
> around it — and divestability is a *demonstrated exit* for every layer (open Delta
> Lake / Delta Sharing, open-source Unity Catalog, OData export, APIs that export as
> OpenAPI to an open-source gateway).

## ✨ What we recommend

- **Two parallel, contained first pilots** — a software-assurance pilot on
  consolidated source control (Track B) and the Artemis supply-chain procurement
  workstream (Track A) — each measurable, each exercising identity + gateway +
  telemetry end to end. The same paved path then serves facilities/asset-management
  and the other Ignition-Day data sets.
- **An LLM gateway** for token governance, multi-model routing, and per-org
  chargeback — the graceful path beyond today's token-broker cost trajectory, while
  keeping model choice open.
- **Cost as a model, not a quote.** Each source's onboarding cost is a function of
  three knowable variables — does an endpoint exist, is the data clean, does the
  code need modernization — so the program can self-estimate a low/high band per
  source before any external quote. Azure infrastructure is priced against live
  Azure list pricing; staffing carries no dollar figures.

## 🚀 What we ask

1. **Confirm the framing** — one platform across data, APIs, and code; Microsoft as
   the interoperability layer, not "the one AI."
2. **Endorse the two parallel first pilots** as the first measurable outcomes.
3. **Direct the follow-ons** — the Artemis worked example, an LLM-gateway
   demonstration, and a resourcing scope against the prioritized inventory.

*De-identified for external sharing. Microsoft Fabric and OneLake are excluded
(not available in Azure Government / GCC); the data platform is Azure Databricks,
Synapse, ADLS Gen2, Azure SQL, Data API Builder, and the open Delta Lake / Delta
Sharing formats. Full detail in the Executive Concept Paper and Technical
Companion.*
