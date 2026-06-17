# Resourcing Framework for an API-First Data Marketplace

### A capability and staffing-pattern model for the OCIO enterprise program

*Prepared by Microsoft Federal — Data, Analytics & AI · For NASA OCIO program planning · Companion to the Executive Concept Paper*

---

## Purpose and scope

This framework answers a single planning question: **what capabilities does the
agency need on the field, and how should it source them**, to stand up and scale
an API-first data marketplace across the enterprise. It is deliberately a
**capability model, not a price quote**. It names the roles, the team shapes, and
a decision method for choosing how to staff each workstream — and it carries **no
vendor names and no dollar figures**, consistent with the program's guidance that
resourcing be framed as capability and pattern rather than a commercial offer.

> **Why no dollars here.** Azure *infrastructure* consumption is priced separately
> and is validated against live Azure list pricing in the Executive Concept Paper
> and Technical Companion. Staffing and professional-services cost is a function of
> the data-set inventory, the modernization depth per source, and the contract
> vehicle the agency selects — it is scoped in a follow-on engagement, not asserted
> here. Treating staffing as a capability model keeps this document durable as
> those variables settle.

## The program at a glance

The directive is an **enterprise entitlement**: mission organizations do not show
up with their own undefined funding to participate; the OCIO leads, coordinates,
and funds the shared platform, and centers connect their data to it on a published
schedule. That model has two consequences for resourcing:

- **A central platform team** owns the shared backbone — the gateway, the
  federated catalog, governance, telemetry, and the LLM gateway — as a product
  with a roadmap, an SLA, and a repeatable onboarding path.
- **A distributed enablement capability** does the per-source work — meeting data
  owners center-to-center and program-to-program, standing up an API on the
  underlying system of record, labeling and cataloging the data, and onboarding it
  to the gateway. This is where the bulk of the effort lives, and it must **scale**:
  the goal is a repeatable onboarding *factory*, not bespoke one-off integrations.

## Capability model — the roles the program needs

The program needs five core capabilities. Each is a *role family*, not a single
hire; an organization can fill a family with civil servants, partners, or a blend.

| Capability | What it does | Primary outcomes |
|---|---|---|
| **Platform engineering** | Builds and operates the shared backbone — API gateway, API catalog, identity integration, telemetry, and the LLM gateway — as a governed product. | A reliable, secure front door and catalog; a paved onboarding path; uptime and policy enforcement across centers. |
| **Data stewardship & governance** | Inventories, classifies, and labels mission data; defines metadata standards; curates catalog entries; owns the federated-catalog discipline. | Trustworthy, discoverable, correctly-labeled data; authoritative-source clarity; the data-quality remediation the program depends on. |
| **Security engineering** | Owns the zero-trust posture, ATO/authorization workflow, sensitivity-label enforcement, software-assurance scanning, and supply-chain integrity. | Compliant exposure of data and APIs; continuous vulnerability scanning and triage; signed, attested builds. |
| **Modernization engineering** | Builds APIs on systems that do not yet expose one; refactors legacy code to expose interfaces; applies LLM-assisted modernization at scale. | New, governed API surfaces over systems of record — the single largest body of work and the program's main cost lever. |
| **Product & program management** | Runs the enterprise entitlement: prioritizes Ignition-Day data sets, sequences center onboarding, manages dependencies, and tracks adoption. | Predictable throughput; a published onboarding schedule; matrixed delivery across centers and mission directorates. |

> **The cost lever is modernization, not the gateway.** Whichever gateway the
> agency selects, the gateway is the smaller, well-understood line. The effort —
> and the staffing — concentrates in building and modernizing the APIs on the
> underlying data sets, and in the data-quality work that has to precede them.
> Resourcing should be sized against the **per-source onboarding** workload and the
> repeatability of the factory that does it.

## Per-source cost-range scoring sheet

The Executive Concept Paper makes the case that a single point quote for
"connecting all the data sets" is not credible before the inventory exists — the
spread between an easy source and a hard one is enormous. This section turns that
argument into a **scoring sheet the agency can run per source, today, with no
external quote and no dollar figures** — producing a relative LOW→HIGH effort band
for each source and, summed across the portfolio, a defensible low/high range.

**Three variables, each scored LOW / MED / HIGH.** Every source is scored on the
same three drivers. The variables are deliberately the ones the agency can assess
itself from its own inventory.

| Variable | LOW | MED | HIGH |
|---|---|---|---|
| **Endpoint exists?** | A usable API/OData endpoint already exists — register and govern it at the gateway. | A partial or legacy interface exists (e.g. SOAP/RFC/flat extract) that must be wrapped or adapted into a clean read API. | No endpoint at all — an API must be built on the underlying system before anything can be exposed. |
| **Data-quality / labeling state?** | Clean, inventoried, correctly labeled — ready to catalog and publish as-is. | Partially inventoried or inconsistently labeled — needs profiling and a targeted steward pass to reach a trustworthy baseline. | Dirty, un-inventoried, or mislabeled — needs full profiling, authoritative-source designation, rule authoring, and re-labeling before exposure. |
| **Modernization depth?** | Modern, maintainable system — no refactor needed to expose an interface. | Some modernization — adapters, wrappers, or moderate refactor to expose a clean interface. | Legacy code that must be substantially modernized (AI-assisted) to expose an interface at all. |

**Turn the three scores into a band.** Read the position, not a number: a source
scoring LOW/LOW/LOW is a thin, repeatable gateway-onboarding job; a source scoring
HIGH/HIGH/HIGH carries the full weight of API construction, data remediation, *and*
modernization. The mix in between sets the band:

| Combined profile | Effort band | What dominates the work |
|---|---|---|
| Mostly LOW | **LOW** | Gateway onboarding + catalog publish; little build, little remediation. |
| Mixed (one or two HIGH) | **MED** | One real cost driver — usually an API build *or* a data-quality remediation *or* a modernization pass. |
| Mostly HIGH | **HIGH** | API construction **and** data remediation **and** modernization stack together. |

**Worked example — three representative archetypes.** Scored on the same sheet, no
dollars:

| Source archetype | Endpoint? | Data quality? | Modernization? | Band | Why |
|---|---|---|---|---|---|
| **Modern science data service** (already exposes an OData/REST endpoint, curated and labeled) | LOW | LOW | LOW | **LOW** | Register the existing endpoint, classify, publish — pure onboarding. |
| **Microsoft surface — Dataverse / SharePoint / M365 Graph** (open OData/REST surface, governable via the same gateway) | LOW | MED | LOW | **LOW–MED** | Endpoint and modernization are non-issues; the only variable is the labeling/steward pass on the content. |
| **Legacy procurement on SAP** (BAPI/RFC integration surface, dirty/un-inventoried records, ERP modernization needed) | HIGH | HIGH | HIGH | **HIGH** | Build the read API/façade, remediate and label the records, and modernize to expose a clean interface — all three drivers active. |

**The onboarding factory is the lever that collapses HIGH toward LOW.** Because the
factory standardizes the expose-façade-catalog-consume stations as templates and
IaC (see the Technical Companion), the *repeatable* portion of even a HIGH source is
done once and reused. What remains source-specific is the genuinely irreducible work
— building an API where none exists and remediating that source's data. Each
additional source therefore costs less than the last, which is precisely how the
program drives its high-end estimate down over time. The single most cost-effective
investment is the factory itself, not any one source.

> **What this is and isn't.** This is a *relative* effort model that the agency
> populates from its own inventory to self-estimate a low/high range across the
> portfolio. It carries **no absolute dollar figures**: Azure *infrastructure*
> consumption is priced separately and validated against live Azure list pricing in
> the Executive Concept Paper and Technical Companion; staffing and
> professional-services cost is scoped in a follow-on engagement against the scored
> inventory and the selected contract vehicle.

## Staffing-pattern options

For each capability, the agency chooses among three sourcing patterns. None is
universally correct; the right choice differs per workstream and is expected to
change over the program's life.

### Pattern A — In-house build
The agency hires and develops the capability internally. **Best when** the work is
enduring, must retain institutional knowledge (data stewardship, governance
standards, authorizing-official functions), or touches the most sensitive
workloads. **Trade-off:** highest control and continuity; slowest to stand up; the
agency must recruit and retain scarce skills.

### Pattern B — Partner-led
A professional-services capability delivers the workstream against the agency's
requirements. **Best when** the work is time-boxed, needs to scale quickly, or
requires deep platform expertise the agency does not intend to retain permanently
(initial platform stand-up, the first wave of modernization, the onboarding-factory
design). **Trade-off:** fastest to capability and scale; requires disciplined
requirements, knowledge-transfer obligations, and an exit plan to avoid dependency.

### Pattern C — Blended
A partner leads while the agency staffs alongside to absorb the capability over
time — the partner builds the first instances and the paved path; agency engineers
take the steady-state and the long tail. **Best when** the agency wants both speed
*and* durable internal capability — which is the typical case for an
enterprise-wide entitlement.

| Pattern | Speed to capability | Control & continuity | Best-fit workstreams |
|---|---|---|---|
| In-house build | Slower | Highest | Data stewardship, governance standards, authorization functions, most-sensitive workloads |
| Partner-led | Fastest | Lower (manage via requirements + KT) | Platform stand-up, first modernization wave, onboarding-factory design |
| Blended | Fast | Grows over time | Enterprise rollout, the modernization long tail, sustained operations |

## A decision framework for choosing per workstream

Apply five questions to each workstream and let the answers point to a pattern:

1. **Durability** — Is this an enduring agency function or a time-boxed build? *Enduring leans in-house or blended; time-boxed leans partner-led.*
2. **Scale & speed** — How fast must it reach enterprise scale? *Aggressive timelines lean partner-led or blended.*
3. **Sensitivity** — Does the workstream touch the most sensitive data or authorizing-official decisions? *Highest sensitivity leans in-house.*
4. **Knowledge retention** — Must the capability live inside the agency afterward? *Yes leans blended with explicit knowledge-transfer.*
5. **Skills availability** — Can the agency recruit and retain the skill in the required window? *Scarce skills lean partner-led or blended while hiring proceeds.*

> **A pragmatic default.** For an enterprise entitlement that must move quickly yet
> leave durable capability behind, a **blended** pattern is the common answer:
> partner-led for the platform stand-up, the first modernization wave, and the
> onboarding-factory design; in-house for data stewardship, governance, and
> authorization; converging toward agency-operated steady state as the factory
> matures. The agency should expect the mix to shift workstream-by-workstream and
> year-over-year.

## Sequencing the capability build

The capability is stood up in step with the program's phased path:

- **Foundation** — Stand up platform engineering and security engineering first;
  they build the shared backbone and the authorization workflow that everything
  else rides on.
- **First pilots** — Add modernization and data-stewardship capacity focused on the
  two first pilots, proving the onboarding factory on a contained, measurable
  scope before scaling.
- **Scale** — Grow the distributed enablement capability and the program-management
  function to drive center-by-center onboarding across the enterprise, with the
  factory and governance patterns established in the pilots.

## What this framework deliberately excludes

- **No dollar figures.** Staffing and professional-services cost is scoped in a
  follow-on engagement against the actual data-set inventory and contract vehicle.
- **No vendor names.** Sourcing patterns are described generically; the agency
  selects providers through its own acquisition process.
- **No headcount mandate.** The role families scale with the inventory; this model
  names the capabilities and the method for sizing and sourcing them, not a fixed
  org chart.

## Next steps

1. Adopt the capability model and confirm the five role families against the
   program's org structure.
2. Run the decision framework across the Foundation and first-pilot workstreams to
   select an initial sourcing pattern per workstream.
3. Commission a follow-on scoping engagement to size staffing and
   professional-services cost against the prioritized Ignition-Day data-set
   inventory and the selected contract vehicle.
