# 🛰️ registry — the control-plane that onboards a data source, live

[Home](../../README.md) > [Services](../) > **registry**

> [!WARNING]
> **Illustrative reference · sample/synthetic data only · not an official NASA
> document.** Every data source this service onboards (Artemis procurement, the DOT
> bridge inventory) is **synthetic**. See **[`docs/DISCLAIMER.md`](../../docs/DISCLAIMER.md)**
> before sharing or adapting.

> [!NOTE]
> **TL;DR** — The registry is the small FastAPI service behind the demo's
> *"+ Add a data source"* wizard. You `POST` it a description of a new API, and it
> **rewrites the gateway's config and hot-reloads it in place** so that the new source is
> instantly governed (JWT + rate-limit + correlation id) and discoverable — **no source
> change, no downtime, no redeploy.** It is the local stand-in for publishing an API in
> **Azure API Management / Azure API Center**. The data never moves; the gateway just
> learns one more upstream.

---

## 📑 Table of contents

- [Why this service exists](#-why-this-service-exists)
- [Where it sits in the bigger picture](#-where-it-sits-in-the-bigger-picture)
- [The Azure mental model (read this first)](#-the-azure-mental-model-read-this-first)
- [The endpoints](#-the-endpoints)
- [What happens when you register a source](#-what-happens-when-you-register-a-source)
- [How a route is built (and why it's never weaker than the built-in one)](#-how-a-route-is-built-and-why-its-never-weaker-than-the-built-in-one)
- [The shared-volume contract with identity and Kong](#-the-shared-volume-contract-with-identity-and-kong)
- [Worked example — onboard the DOT bridge source end-to-end](#-worked-example--onboard-the-dot-bridge-source-end-to-end)
- [Configuration](#-configuration)
- [Gotchas / troubleshooting](#-gotchas--troubleshooting)
- [Where to next](#-where-to-next)
- [Glossary](#-glossary)

---

## 🎯 Why this service exists

Imagine you run a data marketplace. A new team shows up and says: *"We already have an
API in front of our database — please make it available to the rest of the agency, with
the same security and metering everything else gets."*

The expensive, slow answer is: copy their data into your platform, re-model it, redeploy
the gateway with a new hand-edited config, and take a maintenance window to do it. That is
the **data-copy** pattern, and it is exactly what this whole proof-of-concept argues
against.

The registry implements the **API-first, zero-move** alternative. **Zero-move** means the
source's data is never copied; you only register *where its API lives* and *how it should
be governed.* The registry then teaches the gateway about that new upstream — at runtime,
with no restart — so the source becomes a first-class, governed, discoverable product in
seconds.

> **In plain terms:** the registry is the "front desk" of the marketplace. You hand it a
> form describing a new API; it walks over to the gateway, adds the new API to the
> gateway's rulebook, and tells the gateway to re-read the rulebook — all while the
> gateway keeps serving traffic.

> **Why this matters:** the single most compelling moment in the live demo is watching a
> brand-new source go from "doesn't exist" to "governed and queryable through the gateway"
> in one click, with a real correlation id proving the call went through the gateway. The
> registry is the service that makes that moment real instead of staged.

A few words you'll see throughout — defined here once:

| Term | What it means in this repo |
| --- | --- |
| **Gateway** | The single front door all data requests must pass through. Locally this is **Kong OSS**; on Azure it is **Azure API Management**. It enforces auth, rate limits, and metering. |
| **Upstream** | The actual backend API the gateway forwards a request to (e.g. the DOT bridge API). The gateway never *is* the data; it *proxies* to the upstream. |
| **Declarative config** | A single YAML file that fully describes the gateway's behavior — its services, routes, and plugins. Kong runs **DB-less**, meaning this file *is* the source of truth (no database). |
| **Hot reload** | Replacing the gateway's running config without restarting the process or dropping connections. |
| **Source / data product** | A registered API the marketplace governs and lists. |

---

## 🗺️ Where it sits in the bigger picture

The registry is one of several small services on the `edge` network. It does **not** touch
the databases — it only talks to the gateway's admin API and to a shared file.

```mermaid
flowchart LR
    subgraph edge["edge network (client-reachable)"]
        UI["Frontend wizard<br/>(AddSourceWizard.jsx)"]
        REG["registry<br/>:8095"]
        CAT["catalog<br/>:8080"]
        ID["identity<br/>:8081"]
    end
    subgraph internal["internal network (no egress)"]
        DAB["DAB (Artemis SoR)"]
        TRANS["transportation<br/>(DOT source) :8200"]
    end
    KONG["Kong gateway<br/>proxy :8000 / admin :8001"]
    VOL[("shared volume<br/>kong-config<br/>kong.base.yml · kong.yml · sources.json")]

    UI -->|POST /sources| REG
    REG -->|POST /config hot reload| KONG
    REG -.reads base / writes merged + sources.- VOL
    ID -.writes kong.base.yml + initial kong.yml.- VOL
    CAT -.reads sources.json.- VOL
    KONG -.loads kong.yml.- VOL
    KONG --> DAB
    KONG --> TRANS
```

Two things to notice, because they are the heart of the design:

1. **The registry is the only writer of the *merged* config**, but **identity is the
   author of the *base*.** They cooperate through files on a shared volume — never by
   calling each other. ([Details below.](#-the-shared-volume-contract-with-identity-and-kong))
2. **The registry never reaches the data.** It lives on `edge`; the data sources
   (`DAB`, `transportation`) live on the locked-down `internal` network. The only path to
   their data is *through Kong* — which is precisely the zero-move guarantee the registry
   helps deliver. (`tests/test_zero_move.py` proves the data is unreachable directly.)

---

## ☁️ The Azure mental model (read this first)

This proof-of-concept's **primary story is Azure** — you run it locally with open-source
parts to develop and test, then deploy the managed Azure equivalents for the real demo.
The registry's job maps cleanly onto a managed Azure capability, so learn it in those
terms from the start:

| Local (this repo) | Azure managed equivalent | What it does in the onboarding flow |
| --- | --- | --- |
| **registry** service (`POST /sources`) | **Azure API Center** registration + **Azure API Management** import | Records a new API as a governed product and publishes it on the gateway |
| **Kong gateway** (DB-less, `/config` reload) | **Azure API Management** (APIM) | The single governed front door; APIM imports an OpenAPI/backend and applies policies |
| **identity** issuer | **Microsoft Entra ID** | Issues/validates the tokens the gateway checks |
| **catalog** service | **APIM developer portal** / **API Center** catalog | The discoverable storefront of available data products |
| `kong.yml` declarative config | APIM **policies + API definitions** | The rulebook the gateway enforces |

> **In plain terms:** locally the registry *edits a YAML file and tells Kong to reload it.*
> On Azure, the same intent — "publish this backend API behind the managed gateway with
> these policies" — is an APIM API import plus a policy attachment, catalogued in API
> Center. Same outcome; the registry is the OSS rehearsal of the Azure motion.

> [!TIP]
> When you demo this, narrate it as *"this is the Azure API Management import step, shown
> live and locally."* That framing lands the enterprise value better than "I edited a
> Kong file."

---

## 🌐 The endpoints

The registry is a tiny FastAPI app (`services/registry/app.py`) listening on **`:8095`**.
It exposes four endpoints:

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| `GET` | `/healthz` | Liveness probe (used by the Compose healthcheck). | `{"status": "ok"}` |
| `GET` | `/sources` | List the sources registered so far (read from `sources.json`). | `{"sources": [...]}` |
| `POST` | `/sources` | Register a new source: validate → merge into Kong config → hot-reload Kong → persist. | `{"status": "registered", "source": {...}, "gateway_path": "..."}` |
| `DELETE` | `/sources/{source_id}` | Unregister a source: rebuild config from base **without** it → hot-reload → persist. | `{"status": "removed", "id": "..."}` |

### The request body for `POST /sources`

The body is validated by the `SourceSpec` Pydantic model. **Validation happens before
anything touches the gateway** — a malformed request is rejected with HTTP 422 and the
gateway is never disturbed.

| Field | Required | Default | Meaning |
| --- | --- | --- | --- |
| `id` | ✅ | — | URL-safe slug, `^[a-z0-9][a-z0-9-]{1,40}$`. Becomes the Kong service/route name (`src-<id>`). |
| `title` | ✅ | — | Human-readable name shown in the catalog. |
| `upstream_url` | ✅ | — | Where the gateway forwards requests (the **upstream**), e.g. `http://transportation:8200`. |
| `base_path` | ✅ | — | The **gateway** path clients call, e.g. `/dot`. |
| `owner` | — | `"Unspecified"` | Who owns the data product (catalog metadata). |
| `domain` | — | `"Unspecified"` | Business domain (catalog metadata). |
| `classification_label` | — | `"Routine"` | Sensitivity label (the Purview-style governance tag). |
| `require_jwt` | — | `true` | If `true`, the route enforces JWT auth + per-consumer rate limiting. |
| `sample_path` | — | `null` | A ready-to-run example query the catalog/UI can show. |

> [!NOTE]
> **Why a slug for `id`?** The `id` is stitched directly into the Kong service name
> (`src-<id>`) and route name (`route-<id>`). The strict pattern keeps those names valid
> and prevents one source from colliding with or impersonating another.

---

## 🔁 What happens when you register a source

When you call `POST /sources`, the registry performs five ordered steps. The **order
matters**: the gateway is updated *before* the change is persisted, so the on-disk
state never claims success the gateway didn't actually accept.

```mermaid
sequenceDiagram
    autonumber
    actor Op as Operator (UI or curl)
    participant Reg as registry :8095
    participant Vol as shared volume
    participant Kong as Kong admin :8001

    Op->>Reg: POST /sources {id, upstream_url, base_path, ...}
    Reg->>Reg: 1. validate SourceSpec (else 422)
    Reg->>Reg: 2. reject if id already registered (else 409)
    Reg->>Vol: 3a. read kong.base.yml (RSA keys + consumers + Artemis route)
    Reg->>Reg: 3b. merge a service+route+plugins for every source
    Reg->>Kong: 4. POST /config?check_hash=1 (DB-less hot reload)
    Kong-->>Reg: 200/201 OK
    Reg->>Vol: 4b. write merged config to kong.yml (survives Kong restart)
    Reg->>Vol: 5. write sources.json (so catalog lists it; survives registry restart)
    Reg-->>Op: {"status":"registered", "gateway_path":"/dot"}
```

Walking through the code in [`app.py`](app.py):

1. **Validate** (`SourceSpec`, lines 45–54). FastAPI rejects a bad body with **422**
   before any side effects.
2. **De-duplicate** (`add_source`, lines 221–231). If a source with that `id` already
   exists, return **409 Conflict** — you can't silently overwrite a live route.
3. **Merge** (`_build_merged_config`, lines 162–172). Load `kong.base.yml` (the config
   identity rendered, *with* the RSA public keys, the two consumers, and the built-in
   Artemis route intact) and append one `service` per registered source. Existing service
   names are skipped, so the merge is idempotent.
4. **Hot-reload** (`_reload_kong`, lines 175–185). `POST` the *entire* merged declarative
   config to Kong's admin `/config` endpoint with `check_hash=1`. Because Kong runs
   DB-less, this swaps the running config atomically with no restart. A non-2xx response
   becomes **502** and the registry stops — it will *not* persist a config Kong rejected.
5. **Persist** (`_apply` + `_save_sources`, lines 188–229). Only after Kong accepts:
   write the merged config to `kong.yml` (so a *Kong* restart re-loads the new sources)
   and write `sources.json` (so the *catalog* can list them and the registry can rebuild
   on its own restart).

> **Why this matters:** "reload first, persist second" means the gateway is the
> authority. If the gateway refuses a config, the demo doesn't end up with a `sources.json`
> entry for a source that isn't actually live. That is the difference between a control
> plane you can trust and one that lies to you.

`DELETE /sources/{id}` (lines 234–242) is the mirror image: filter the source out, rebuild
the merged config **from base** (so the route disappears cleanly with no leftover state),
hot-reload, and persist. A delete of an unknown id returns **404**.

---

## 🧱 How a route is built (and why it's never weaker than the built-in one)

`_kong_route_for(src)` (lines 70–159) constructs the Kong service + route + plugin stack
for one source. **Crucially, a wizard-added source gets the *same* governance controls as
the first-party Artemis route in [`services/gateway/kong.yml`](../gateway/kong.yml).** A
federated source must never be a softer target than the built-in one.

| Plugin | Applied when | Why it's there |
| --- | --- | --- |
| `correlation-id` | always | Stamps + echoes `X-Correlation-ID` so a consumer can *prove* the response came through Kong. |
| `jwt` | `require_jwt: true` | Reject missing/invalid tokens at the edge (**401**); maps the call to a consumer via the `client_id` claim. |
| `rate-limiting` | `require_jwt: true` | Per-consumer quota (`limit_by: consumer`); over the cap returns **429**. |
| `cors` | always | Lets the browser SPA call the gateway (GET/OPTIONS) and read `X-Correlation-ID`. |
| `pre-function` | always | **OWASP API4** guard: rejects over-broad extraction (`$first > 200`) **before** the request reaches the upstream. |
| `request-transformer` | always | Strips client-supplied identity headers (`X-MS-CLIENT-PRINCIPAL*`, `X-MS-API-ROLE`) so the upstream can't be tricked into serving a privileged, un-redacted role. |

> **In plain terms:** even a "public" (no-JWT) source still gets the abuse guard and the
> identity-header scrub. You can drop the lock on the front door, but you can't disable the
> burglar alarm.

> [!NOTE]
> **OWASP API4** is the "Unrestricted Resource Consumption" risk from the OWASP API
> Security Top 10. The `pre-function` Lua snippet caps `$first` at 200 so a single call
> can't siphon the entire dataset.

The service object it returns looks like this (for `base_path: /dot`):

```jsonc
{
  "name": "src-dot-bridges",
  "url": "http://transportation:8200",        // the upstream
  "routes": [
    {
      "name": "route-dot-bridges",
      "paths": ["/dot"],
      "strip_path": true                       // /dot/api/Bridge -> upstream sees /api/Bridge
    }
  ],
  "plugins": [ /* correlation-id, jwt, rate-limiting, cors, pre-function, request-transformer */ ]
}
```

> [!IMPORTANT]
> **`strip_path: true` is deliberate.** The gateway prefix (`/dot`) is removed before
> forwarding, so the upstream receives *its own native path* (`/api/Bridge`). The upstream
> doesn't need to know or care what public path the gateway chose for it — that's what
> lets you front an *existing, unmodified* API.

This parity is not left to good intentions — it is **tested**.
[`tests/test_registry_config.py`](../../tests/test_registry_config.py) imports
`_kong_route_for` directly (no running stack needed) and asserts the full governance set is
present, that safety controls survive even with `require_jwt: false`, and that the
identity-spoofing headers are stripped. If a future edit drops a plugin, CI fails.

---

## 🤝 The shared-volume contract with identity and Kong

This is the subtle, important part. Three services cooperate **only through files** on a
Docker volume named `kong-config` (mounted at `/shared`). None of them call each other to
coordinate config — they read and write agreed-upon files. This decoupling is what lets
each service restart independently without losing state.

```mermaid
flowchart TD
    ID["identity (startup)"] -->|writes| BASE["/shared/kong.base.yml<br/>(canonical base: RSA keys, consumers, Artemis route)"]
    ID -->|writes if absent| RENDERED1["/shared/kong.yml<br/>(initial effective config)"]
    REG["registry"] -->|reads| BASE
    REG -->|writes merged| RENDERED2["/shared/kong.yml<br/>(base + all sources)"]
    REG -->|writes| SRC["/shared/sources.json"]
    KONG["Kong"] -->|loads on (re)start| RENDERED2
    CAT["catalog"] -->|reads| SRC
```

The three files and who owns them:

| File | Written by | Read by | Purpose |
| --- | --- | --- | --- |
| `kong.base.yml` | **identity** (on startup) | **registry** | The canonical base: the rendered RSA public key, the two consumers, the built-in Artemis route. The registry treats this as read-only and merges sources *on top of* it. |
| `kong.yml` | **identity** (initial) → then **registry** (merged) | **Kong** | The *effective* config Kong actually loads. Identity writes a valid initial copy so Kong has something to boot with; the registry overwrites it with base+sources on every change. |
| `sources.json` | **registry** | **catalog** | The list of registered sources, so the catalog can list them and the registry can rebuild after its own restart. |

Why split base from effective? Three independent restart guarantees fall out of it:

- **Kong restarts** → it re-reads `kong.yml`, which already contains every registered
  source. The sources survive even if the registry is down.
- **The registry restarts** → its startup hook (`_startup`, lines 199–208) re-reads
  `sources.json`, rebuilds the merged config from base, and re-applies it to Kong. State
  is reconstructed from the file, not held in memory.
- **A `DELETE`** → because the merge always starts *from base*, removing a source just
  rebuilds base + the remaining sources. There is no stale leftover route to clean up.

> [!IMPORTANT]
> The registry mounts `kong-config` **read-write** (`/shared`), because it must write
> `kong.yml` and `sources.json`. Kong mounts the same volume **read-only**
> (`/shared:ro`) and the catalog mounts it **read-only** too. See the `volumes:` blocks in
> [`docker-compose.yml`](../../docker-compose.yml) (registry ~L202, kong ~L145, catalog
> ~L174). Identity also mounts it read-write so it can render the base.

> **Why this matters:** the RSA keys live only in this volume and are *never committed*.
> By reading the identity-rendered base instead of regenerating config, the registry
> guarantees the consumers and signing key the gateway already trusts are preserved — so a
> token minted before you added a source still works after.

---

## 🧪 Worked example — onboard the DOT bridge source end-to-end

This is the exact flow the demo performs. It registers the synthetic DOT bridge API as a
second source and proves it is governed identically to Artemis. Run these from a shell with
the `core` stack already up (`make demo`).

> [!NOTE]
> Host ports below assume the defaults. If you remapped ports to avoid local collisions,
> substitute your mapped host ports for `8095` (registry), `8081` (identity), and `8000`
> (Kong proxy).

**1. Register the source.** The registry validates it, merges the route, and hot-reloads
Kong:

```bash
curl -s -X POST http://localhost:8095/sources \
  -H 'Content-Type: application/json' \
  -d '{
    "id": "dot-bridges",
    "title": "DOT Transportation - Bridge Inventory",
    "upstream_url": "http://transportation:8200",
    "base_path": "/dot",
    "owner": "US DOT (synthetic)",
    "domain": "Transportation / Infrastructure",
    "classification_label": "Routine",
    "require_jwt": true,
    "sample_path": "/dot/api/Bridge?$orderby=condition_rating asc&$first=5"
  }' | jq .
```

Expected output:

```json
{
  "status": "registered",
  "source": {
    "id": "dot-bridges",
    "title": "DOT Transportation - Bridge Inventory",
    "upstream_url": "http://transportation:8200",
    "base_path": "/dot",
    "owner": "US DOT (synthetic)",
    "domain": "Transportation / Infrastructure",
    "classification_label": "Routine",
    "require_jwt": true,
    "sample_path": "/dot/api/Bridge?$orderby=condition_rating asc&$first=5"
  },
  "gateway_path": "/dot"
}
```

*What just happened:* the registry merged a `src-dot-bridges` service into the Kong config
and Kong hot-reloaded it. The `/dot` route now exists. No process restarted.

**2. Mint a token** from the identity issuer (the Entra ID stand-in):

```bash
TOKEN=$(curl -s -X POST http://localhost:8081/token \
  -H 'Content-Type: application/json' \
  -d '{"consumer":"analyst"}' | jq -r .access_token)
```

**3. Query the NEW source through the gateway** — note we hit Kong on `:8000`, never the
upstream directly:

```bash
curl -s -i -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/dot/api/Bridge?\$orderby=condition_rating%20asc&\$first=3" \
  | grep -iE '^(HTTP|X-Correlation-ID)'
```

Expected (header excerpt):

```text
HTTP/1.1 200 OK
X-Correlation-ID: a1b2c3d4-...
```

*What just happened:* Kong accepted the token (mapping it to the `analyst` consumer),
applied rate-limiting and the OWASP guard, forwarded `/dot/api/Bridge` to the upstream as
`/api/Bridge` (path stripped), and stamped the `X-Correlation-ID`. The presence of that
header is your **proof** the call went through the gateway — the upstream never sets it.

**4. Prove the edge enforces auth** — same path, no token:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/dot/api/Bridge
```

Expected output:

```text
401
```

*What just happened:* the `jwt` plugin rejected the request at the edge. The DOT upstream
was never contacted — exactly the behavior the built-in Artemis route has.

**5. Confirm it's discoverable** — the catalog now lists it from `sources.json`:

```bash
curl -s http://localhost:8080/catalog | jq '.products[] | {id, title}'
```

**6. Clean up** (hot-reload removes the route):

```bash
curl -s -X DELETE http://localhost:8095/sources/dot-bridges | jq .
```

Expected output:

```json
{ "status": "removed", "id": "dot-bridges" }
```

> [!TIP]
> The UI wizard ([`frontend/src/components/AddSourceWizard.jsx`](../../frontend/src/components/AddSourceWizard.jsx))
> drives this exact same `POST /sources` call across a 4-step form
> (Identify → Connect → Govern → Review & publish). The API and the wizard are two faces
> of the same control-plane — see [`docs/ADD-A-SOURCE.md`](../../docs/ADD-A-SOURCE.md).

---

## ⚙️ Configuration

All configuration is via environment variables (set in [`docker-compose.yml`](../../docker-compose.yml)).
Defaults shown are the in-code fallbacks from [`app.py`](app.py).

| Variable | Default (code) | Set in Compose to | Purpose |
| --- | --- | --- | --- |
| `REGISTRY_PORT` | `8095` | `8095` | Port the registry listens on. |
| `KONG_ADMIN_INTERNAL_URL` | `http://kong:8001` | `http://kong:8001` | Kong **admin** API — where the hot reload is POSTed. |
| `KONG_BASE` | `/shared/kong.base.yml` | _(default)_ | The canonical base config to merge on top of (written by identity). |
| `KONG_RENDERED` | `/shared/kong.yml` | `/shared/kong.yml` | The effective config Kong loads; the registry overwrites it with base+sources. |
| `SOURCES_FILE` | `/shared/sources.json` | `/shared/sources.json` | Persisted source list (also read by the catalog). |
| `RATE_LIMIT_PER_MINUTE` | `60` | `${RATE_LIMIT_PER_MINUTE:-60}` | Per-consumer rate limit baked into each governed route. |

Stack: **Python 3.11 · FastAPI · httpx · PyYAML · uvicorn** on `python:3.11-slim`
(see [`Dockerfile`](Dockerfile) and [`requirements.txt`](requirements.txt)). The container
is part of the `core` Compose profile and waits on **both** Kong and identity being healthy
(`depends_on: condition: service_healthy`) — it cannot apply a config until identity has
rendered the base and Kong is up.

---

## 🧯 Gotchas / troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `503 base Kong config /shared/kong.base.yml not found yet` | The registry started before identity rendered the base. | Confirm `identity` is healthy; the `depends_on` should prevent this, but on a cold volume give it a moment and retry. |
| `502 Kong reload failed: ...` | Kong rejected the merged config (bad upstream URL, malformed path, plugin error). | Read the message — it includes Kong's response. The registry did **not** persist, so on-disk state is still consistent; fix the source spec and re-POST. |
| `409 source '<id>' already registered` | An `id` collision. | Use a unique `id`, or `DELETE` the existing one first. |
| `422 Unprocessable Entity` on POST | `SourceSpec` validation failed (often the `id` slug pattern). | `id` must match `^[a-z0-9][a-z0-9-]{1,40}$`; ensure required fields are present. |
| New route returns `404` through Kong | `base_path` typo, or you queried the upstream's native path on the gateway without the prefix. | Call `{base_path}` + the upstream's path (e.g. `/dot/api/Bridge`); the gateway strips `/dot` before forwarding. |
| Source vanished after `docker compose down -v` | `-v` removes the `kong-config` volume (and `sources.json`). | Expected — that volume holds the registered-sources state. Re-register, or omit `-v`. |
| Sources gone after restarting only the registry | None — they shouldn't be. | The startup hook rebuilds from `sources.json`. If they're gone, check the volume mount is read-write for the registry. |

> [!WARNING]
> The registry's CORS is wide open (`allow_origins=["*"]`) and there is **no auth on the
> registry's own endpoints** — appropriate for a self-contained local demo, **not** for
> production. On Azure, the control-plane motion is an authenticated APIM/API Center
> operation behind Entra ID, not an open `POST`.

---

## 🧭 Where to next

- **[`docs/ADD-A-SOURCE.md`](../../docs/ADD-A-SOURCE.md)** — the full onboarding walkthrough
  (UI wizard *and* API), including federating the real published Azure DOT DAB demo.
- **[`services/gateway/`](../gateway/)** — the canonical `kong.yml` whose governance the
  registry mirrors for every new source.
- **[`services/identity/`](../identity/)** — the issuer that renders `kong.base.yml` (the
  base the registry merges onto) and mints the tokens the routes enforce.
- **[`services/catalog/`](../catalog/)** — reads `sources.json` to make every registered
  source discoverable.
- **[`services/transportation/`](../transportation/)** — the synthetic DOT source used as
  the second upstream in the worked example.
- **[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md)** · **[`docs/ZERO-MOVE.md`](../../docs/ZERO-MOVE.md)**
  · **[`docs/APIM-CAPABILITIES.md`](../../docs/APIM-CAPABILITIES.md)** — the architecture,
  the zero-move proof, and the Azure API Management mapping.

---

## 📖 Glossary

| Term / acronym | Definition |
| --- | --- |
| **API-first** | Expose data *as a governed API* rather than copying it; the API contract is the product. |
| **Zero-move** | The data is never copied out of its system of record; consumers reach it only through the gateway. |
| **Control-plane** | The management layer that configures *how* the system behaves (here: the registry adding routes) — as opposed to the data-plane that serves traffic (Kong proxying requests). |
| **Gateway / Kong** | The single governed front door for all data requests (local: Kong OSS; Azure: API Management). |
| **Upstream** | The backend API the gateway forwards a request to. |
| **DB-less** | Kong running with no database; a declarative YAML file is the entire source of truth. |
| **Declarative config** | The YAML (`kong.yml`) that fully describes Kong's services, routes, and plugins. |
| **Hot reload** | Swapping the gateway's running config in place, with no restart or dropped connections. |
| **Plugin** | A Kong policy module (jwt, rate-limiting, cors, correlation-id, pre-function, request-transformer). |
| **JWT** | JSON Web Token — the signed bearer token the `jwt` plugin validates at the edge. |
| **Correlation id** | A per-request id (`X-Correlation-ID`) the gateway stamps, proving a response came through Kong. |
| **OWASP API4** | "Unrestricted Resource Consumption" from the OWASP API Security Top 10; here, the `$first ≤ 200` extraction cap. |
| **strip_path** | Kong route option that removes the gateway prefix (`/dot`) before forwarding to the upstream. |
| **SoR (System of Record)** | The authoritative source database (here, the Artemis Postgres + DAB). |
| **DAB** | Microsoft **Data API Builder** — auto-generates REST/GraphQL over a database. |
| **APIM** | **Azure API Management** — the managed Azure gateway the local Kong stands in for. |
| **Entra ID** | **Microsoft Entra ID** — the managed Azure identity provider the local issuer stands in for. |
| **Purview** | **Microsoft Purview** — Azure data governance/classification; the `classification_label` is its local analogue. |

---

> _Synthetic data only. This document is an illustrative reference, not an official NASA
> document. See [`docs/DISCLAIMER.md`](../../docs/DISCLAIMER.md)._
