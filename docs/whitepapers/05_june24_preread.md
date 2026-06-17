# Pre-Read — API-First Data Marketplace for the Mission Enterprise

### A short brief ahead of the June 24 OCIO discussion

*Prepared by Microsoft Federal — Data, Analytics & AI · For the June 24 OCIO session · Read time ≈ 5 minutes*

---

## Why you're reading this

The agency is preparing an Administrator-level directive that will ask every
organization to expose its mission data through governed APIs, discoverable in an
enterprise catalog, with access controls — an enterprise entitlement led and
coordinated by the OCIO, targeted at the next fiscal year. This pre-read frames
**how Microsoft supports the API-first, multi-model, zero-move architecture you
have already chosen**, so the June 24 discussion can move quickly to decisions.

The full detail lives in two companion documents — an **Executive Concept Paper**
and a **Technical API-First Companion**. This page is the orientation.

> **The one-sentence frame.** You are not buying "one AI." You are building an AI
> *ecosystem* — many models, many vendors, data spread across centers. Microsoft's
> role is the **secure interoperability, orchestration, and governance layer** that
> makes that ecosystem work, on open standards, with the least possible burden on
> the systems you already run.

## What we heard, in your words

- **Zero copy.** Petabytes of data; no medallion rebuild. Catalog the metadata,
  connect compute where it's needed, and keep data in its system of record.
- **The real blocker is data quality, not access control.** Identity and access
  controls largely work; the data is un-inventoried and inconsistently labeled.
  Governance comes first.
- **Avoid vendor lock-in.** Modular, divestable components — an open metadata
  catalog, an open storage and sharing format, and an open-source-leaning,
  self-hosted API gateway.
- **Start where it's already moving.** Ignition-Day missions (Artemis III, Moon
  Base, SR-1 Freedom) take precedence; the Artemis supply-chain (procurement)
  workstream is already in flight.
- **Software assurance is priority one alongside API-first.** Scanning in-house
  code for vulnerabilities, and modernizing it — increasingly with LLMs — is a top
  cybersecurity need.
- **The LLM cost trajectory matters.** Today's token-broker approach will become
  too expensive as coding usage grows; a gateway pattern for token governance,
  multi-model routing, and per-org chargeback is of direct interest.

## What Microsoft proposes

**One platform that catalogs and governs three asset classes — data, APIs, and
code — over a shared, vendor-neutral backbone**, with LLMs as both the scaling
lever and a governed consumption surface. Two interlocked tracks ride the same
backbone:

- **Track A — API-first data exposure.** Open-source path and managed path,
  presented honestly side by side. Microsoft surfaces (Dataverse, GitHub,
  SharePoint, M365 Graph) are treated as first-class API-first sources.
- **Track B — Software assurance & code modernization.** Consolidated source
  control as the code inventory; LLM-driven vulnerability scanning and triage;
  LLM-assisted refactoring to expose APIs from legacy code; security specs as
  catalog entries; API risk controls enforced at the gateway; supply-chain
  integrity.

The **shared backbone** is a gateway + a federated catalog (data, APIs, and code) +
governance + telemetry + an LLM gateway. The gateway runs *next to the data*, so
nothing moves to be exposed or governed.

> **Why this lands, in one line.** The agency's identity is already Microsoft
> Entra ID — the same identity substrate sits under the gateway's token validation,
> the LLM gateway's per-consumer metering, and the zero-trust wrap over the whole
> fabric, so it is the moat. The agency already owns the API surfaces the directive
> will require it to expose — Dataverse, GitHub, SharePoint, and M365 Graph — so
> there is nothing to acquire. Stated plainly: **we do not need to win the gateway**
> (it can be open-source and divestable). We win on the identity already in place,
> the surfaces the agency already owns, the LLM economics at the gateway, and the
> code-assurance layer around it.

## The two first pilots

We propose **two parallel, contained, measurable first pilots** — one per track —
rather than tying the first deliverable to a single in-flight effort:

| Pilot | Track | Why it's the right first step |
|---|---|---|
| **GitHub consolidation + software assurance** | B | Contained and measurable; produces the code inventory that software assurance and modernization require; exercises identity, gateway, and telemetry end to end. *(This is the GitHub team's workstream — referenced here, delivered there.)* |
| **Artemis supply-chain (procurement)** | A | Already in flight with data owners identified; SAP procurement data → governed API façade → catalog entry → consumable downstream. Proves the zero-move data pattern on an Ignition-Day priority. |

The same onboarding-factory pattern applies directly to the facilities /
asset-management (Maximo-style) use case — so prioritizing the two pilots doesn't
drop that audience's priority; it builds the paved path that facilities and the
other enterprise use cases then ride.

## Who's at the table, and what each gets from this

| Stakeholder | What this program offers you |
|---|---|
| **Chief Data & AI Officer** | An enterprise entitlement that scales across centers with one governance model; a credible answer to the LLM cost trajectory; a phased path with measurable first pilots. |
| **Platform engineering** | A managed-and-open gateway choice presented with honest trade-offs; a paved, repeatable onboarding path; APIM as the LLM gateway with token governance and per-org chargeback. |
| **Use-case delivery** | The data connections that power enterprise use cases — exposed in place, discoverable in a catalog, governed centrally. |
| **Policy & metadata standards** | A federated-catalog discipline and a data-stewardship capability that put governance and correct labeling first — the actual blocker. |
| **Power Platform / Dataverse owner** | Dataverse as a first-class API-first surface: an open OData v4 Web API with `$metadata` discovery, governed through the same gateway as everything else. |

## What we're asking for on June 24

1. **Confirm the framing** — one platform across data, APIs, and code; Microsoft as
   the interoperability layer, not "the one AI."
2. **Endorse the two parallel first pilots** as the program's first measurable
   outcomes.
3. **Direct the follow-ons** — a working Artemis worked example (synthetic
   procurement data), an APIM-as-LLM-gateway demonstration, and a follow-on
   resourcing scope.

## Where the detail lives

- **Executive Concept Paper** — the unifying executive summary across data, APIs,
  and code; the two tracks; the LLM gateway; the phased path; the resourcing frame.
- **Technical API-First Companion** — reference architecture, code patterns, sample
  APIs (Dataverse Web API / `$metadata`, M365 Graph, SharePoint), the ATO and
  sensitivity-label flow, the scanning pipeline, gateway sizing, and the
  APIM-as-LLM-gateway pattern.
- **Artemis Worked Example** — the end-to-end pattern on synthetic procurement data.
- **Resourcing Framework** — capability model and staffing patterns (no dollar
  figures, no vendor names).
