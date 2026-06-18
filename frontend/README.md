<!-- breadcrumb -->
[nasa-api-first-poc](../README.md) › **frontend**

# 🛰️ Marketplace SPA — the human face of the API-first gateway

> [!NOTE]
> **TL;DR** — This folder is a small [Vite](https://vitejs.dev/)-built [React](https://react.dev/) single-page app (SPA) that *demonstrates* the whole point of the platform: a person can browse a catalog of governed data products and **query them live — and every single data call goes through the [Kong](https://konghq.com/) gateway**, never directly to a database. The UI holds no secrets and talks to no source directly; it asks the local identity issuer for a token, then calls Kong with that token. You develop it with `npm run dev` (hot-reload at `:5173`) and demo it with `make ui` (built + served by nginx in Docker). The same code runs in Azure; only a tiny runtime config file changes.

> [!WARNING]
> **Synthetic data only.** Everything this UI displays is **synthetic** — not real NASA, DOT, or any agency records. It is ITAR/CUI-safe sample data generated for the proof-of-concept. See [`docs/DISCLAIMER.md`](../docs/DISCLAIMER.md).

---

## 📚 Table of contents

- [Why this UI exists (read this first)](#-why-this-ui-exists-read-this-first)
- [The Azure story, and what the local UI stands in for](#-the-azure-story-and-what-the-local-ui-stands-in-for)
- [Architecture at a glance](#-architecture-at-a-glance)
- [The golden rule: every data call goes THROUGH Kong](#-the-golden-rule-every-data-call-goes-through-kong)
- [Project layout](#-project-layout)
- [Runtime config: `config.js` and `window.APP_CONFIG`](#-runtime-config-configjs-and-windowapp_config)
- [`liveOnboarding`: the same build, two environments](#-liveonboarding-the-same-build-two-environments)
- [Component-by-component walkthrough](#-component-by-component-walkthrough)
- [`make ui` vs `npm run dev` — two ways to run](#-make-ui-vs-npm-run-dev--two-ways-to-run)
- [Worked example: query Artemis-3 supply risk through the gateway](#-worked-example-query-artemis-3-supply-risk-through-the-gateway)
- [Accessibility (Section 508 / WCAG 2.1 AA)](#-accessibility-section-508--wcag-21-aa)
- [Gotchas & troubleshooting](#-gotchas--troubleshooting)
- [Where to next](#-where-to-next)

---

## 🎯 Why this UI exists (read this first)

Imagine you are explaining the platform to an executive who has never seen it. You can *say* "we put every data product behind one governed gateway, so nothing moves and everything is authenticated, rate-limited, and metered." That sentence is abstract. This UI makes it **visible and clickable** in about ten seconds:

1. The visitor sees a **marketplace** of data products (cards).
2. They click one and press **"Run through gateway"**.
3. Rows come back — *and* the screen prints the HTTP status and the gateway's **correlation id**, the unique id [Kong](https://konghq.com/) stamps on every request so it can be traced end-to-end.
4. With the live-onboarding wizard, they can **publish a brand-new data source** and watch it answer through the gateway moments later — no database change, no downtime.

**In plain terms:** the SPA is a *salesperson and a proof* at the same time. It tells the story (zero-move, governed-at-the-edge, add-a-source-in-seconds) and then proves each claim by making a real, traceable call.

**Why this matters:** the architectural claim of this whole repo is that data **never moves** — clients reach it *only* through the gateway. A demo where the browser quietly talked straight to a database would silently contradict that claim. So the UI is deliberately built to have **exactly one path to data: through Kong.** That discipline lives in [`src/api.js`](src/api.js) and is the single most important thing to understand here.

> **Define-on-first-use**
> - **SPA (single-page application):** a web app that loads one HTML page and then updates the view with JavaScript instead of navigating to new pages.
> - **Gateway:** a single front door that all API traffic passes through; it authenticates, rate-limits, logs, and routes requests to the real backend ("upstream"). Here that is Kong.
> - **Zero-move:** the data stays in its system of record; consumers query it in place through the gateway rather than copying ("moving") it into a new store.

---

## ☁️ The Azure story, and what the local UI stands in for

This is an **enterprise proof-of-concept**, and its primary message is *"deploy to Azure to show the full art of the possible."* Local Docker is the **dev/test loop** — you run it locally to build and test, and you deploy to Azure for the real demo. The beauty of this SPA is that **the exact same compiled bundle runs in both places**; only the small runtime [`config.js`](#-runtime-config-configjs-and-windowapp_config) file changes.

Every local open-source component this UI talks to is the stand-in for an Azure managed service:

| The UI calls this locally | …which stands in for this Azure managed service | Why the mapping holds |
| --- | --- | --- |
| **Kong gateway** (`config.kong`) | **Azure API Management (APIM)** | Both are the one governed front door: JWT validation, rate-limit, metering, routing. |
| **Local RS256 JWT issuer** (`config.identity`) | **Microsoft Entra ID** | Both mint signed bearer tokens the gateway validates. The local issuer uses the same RS256 pattern. |
| **Catalog / registry FastAPI services** (`config.catalog`, `config.registry`) | **Azure Container Apps** (the API host) + **Azure API Center** (the catalog) | Container Apps hosts the small services; API Center is the managed catalog of published APIs. |
| **The onboarding wizard's "publish a source"** | **Publishing an API in Azure API Management / API Center** | Same gesture — register an existing upstream and govern it — done through the managed plane in Azure. |

> [!TIP]
> When you demo, narrate the mapping out loud: *"This card list is our catalog — in Azure that's API Center. This 'Run through gateway' button hits Kong — in Azure that's API Management. This token came from a local issuer — in Azure that's Entra ID."* The UI is the storyboard; Azure is the production set.

---

## 🗺️ Architecture at a glance

```mermaid
flowchart LR
    subgraph browser["🌐 Browser — the SPA (this folder)"]
        UI["React UI<br/>App / QueryConsole / Wizard"]
        CFG["window.APP_CONFIG<br/>(from config.js)"]
        API["api.js<br/>(the ONLY network layer)"]
        UI --> API
        CFG -. configures .-> API
    end

    API -->|"1 POST /token"| ID["🔐 Identity issuer<br/>(→ Entra ID)"]
    API -->|"2 GET /catalog (no token)"| CAT["📇 Catalog svc<br/>(→ API Center)"]
    API -->|"3 GET/POST /sources (no token)"| REG["🛠️ Registry / control-plane"]
    API -->|"4 GET /api/... + Bearer token"| KONG["🚪 Kong gateway<br/>(→ API Management)"]

    KONG -->|routes to upstreams<br/>on the internal network| SRC["🗄️ Postgres + DAB + DOT API<br/>(unreachable directly)"]

    classDef edge fill:#13347f,stroke:#50e6ff,color:#fff;
    classDef secret fill:#0a1f4d,stroke:#fc3d21,color:#fff;
    class KONG,ID,CAT,REG edge;
    class SRC secret;
```

The four arrows from `api.js` are the **only** four kinds of network calls this app makes. Three of them (token, catalog, registry) are control-plane conveniences. The fourth — the **data** call — *always* carries a bearer token and *always* targets Kong. There is no fifth arrow to a database.

---

## 🔒 The golden rule: every data call goes THROUGH Kong

All network access is centralized in one file, [`src/api.js`](src/api.js), so the rule is easy to audit. Here is the function that fetches data:

```js
// src/api.js — GET through the gateway with a bearer token.
export async function gatewayGet(path, consumer = "analyst") {
  const token = await getToken(consumer);                       // ① mint a token
  const r = await fetch(`${CFG.kong}${path}`, {                 // ② call KONG, not a DB
    headers: { Authorization: `Bearer ${token}` },              // ③ present the token
  });
  const correlationId = r.headers.get("X-Correlation-ID");      // ④ read the trace id
  let raw = null;
  try { raw = await r.json(); } catch { raw = null; }
  return { status: r.status, rows: raw?.value || [], correlationId, raw };
}
```

Walk through what each step *teaches*:

1. **`getToken(consumer)`** — the UI never hard-codes a credential. It asks the identity issuer (`CFG.identity`) for a fresh signed token for a named consumer (`analyst` or `artemis-agent`). This is the local stand-in for an app getting a token from **Entra ID**.
2. **`fetch(\`${CFG.kong}${path}\`)`** — the data request goes to **Kong's base URL** (`CFG.kong`, e.g. `http://localhost:8000`). Note what is *absent*: there is no Postgres host, no database port, no SQL. The browser literally does not know where the data lives.
3. **`Authorization: Bearer <token>`** — without this header the gateway returns **401** before the request ever reaches a source. The token is how Kong identifies the consumer for auth, rate-limiting, and metering.
4. **`X-Correlation-ID`** — Kong stamps every response with a trace id. The UI surfaces it so a presenter can say "this exact call is now traceable in Grafana." (Grafana/Prometheus here stand in for **Azure Monitor + Sentinel**.)

The `rows: raw?.value || []` line is worth a note: the backend speaks **OData**, an open REST query standard, which wraps result rows in a top-level `value` array. So `raw.value` is the list of rows, and the optional chaining (`?.`) keeps the UI from crashing if a non-OData or error body comes back.

> [!NOTE]
> **Why centralizing matters.** Because *only* `api.js` calls `fetch`, you can prove the zero-move property by reading one file. The repo even has a test, [`tests/test_zero_move.py`](../tests/test_zero_move.py), that proves Postgres and Data API Builder are unreachable from the client network — the network topology enforces what the code promises.

---

## 🧱 Project layout

```text
frontend/
├─ index.html              # HTML shell; loads /config.js BEFORE the app, mounts #root
├─ package.json            # deps (react, react-dom) + scripts (dev/build/preview)
├─ vite.config.js          # Vite + React plugin; dev server on :5173
├─ public/
│  └─ config.js            # ⚙️ runtime config → sets window.APP_CONFIG (the source of truth)
├─ src/
│  ├─ main.jsx             # React entry: mounts <App/> into #root (StrictMode)
│  ├─ App.jsx              # top-level layout: masthead, banner, catalog grid, panels, footer
│  ├─ api.js               # 🔒 the ONLY network layer — all data goes through Kong
│  ├─ styles.css           # design system + all accessibility CSS
│  └─ components/
│     ├─ Emblem.jsx        # original SVG mission emblem (not the NASA logo)
│     ├─ QueryConsole.jsx  # query a selected product THROUGH the gateway; shows correlation id
│     ├─ AddSourceWizard.jsx # 4-step "publish an existing API" flow (live-onboarding only)
│     └─ ResultTable.jsx   # renders any list of row objects as an accessible table
├─ Dockerfile             # multi-stage: Vite build → nginx serves static files
└─ nginx.conf             # SPA fallback + "never cache config.js"
```

> [!TIP]
> Two folders you will see locally are **not** in source control: `node_modules/` (installed deps) and `dist/` (the Vite build output) are both git-ignored. Treat `dist/` as a throwaway artifact — the **source of truth for runtime config is [`public/config.js`](public/config.js)**, which Vite copies into `dist/` at build time.

---

## ⚙️ Runtime config: `config.js` and `window.APP_CONFIG`

A normal React build "bakes in" environment values at compile time. That would force you to **rebuild the app for every environment** (local, Azure dev, Azure demo). This SPA avoids that with a classic, robust pattern: **runtime configuration via a global object.**

In [`index.html`](index.html), a tiny script loads *before* the app bundle:

```html
<!-- index.html -->
<script src="/config.js"></script>          <!-- runs FIRST, defines window.APP_CONFIG -->
...
<script type="module" src="/src/main.jsx"></script>  <!-- the React app, runs AFTER -->
```

That `/config.js` is [`public/config.js`](public/config.js). Vite copies anything in `public/` to the web root verbatim, so the file ships next to `index.html`:

```js
// public/config.js — runtime config (browser-side URLs to the gateway / issuer / catalog).
window.APP_CONFIG = {
  kong: "http://localhost:8000",      // the gateway — ALL data calls go here
  identity: "http://localhost:8081",  // token issuer (→ Entra ID)
  catalog: "http://localhost:8080",   // catalog service (→ API Center)
  registry: "http://localhost:8095",  // control-plane for live onboarding
  liveOnboarding: true,               // show the "add a source" wizard? (see below)
};
```

[`src/api.js`](src/api.js) reads it on load, with a sane fallback so the dev server still works even if the file is missing:

```js
// src/api.js
const CFG = window.APP_CONFIG || {
  kong: "http://localhost:8000",
  identity: "http://localhost:8081",
  catalog: "http://localhost:8080",
  registry: "http://localhost:8095",
};
export const ENDPOINTS = CFG;  // also rendered in the page footer for transparency
```

**In plain terms:** you build the app **once**. To point it at Azure, you don't recompile — you **swap one small JavaScript file**. The `nginx.conf` even sends `Cache-Control: no-store` for `/config.js` specifically, so a redeploy's new config is never served stale from a browser cache:

```nginx
# frontend/nginx.conf
location = /config.js {
    add_header Cache-Control "no-store";   # runtime config — never cache it
}
location / {
    try_files $uri $uri/ /index.html;      # SPA fallback: deep links resolve to the app
}
```

> [!NOTE]
> **How to point the UI at Azure (or remapped local ports).** Mount a different `config.js` into the nginx container's web root (`/usr/share/nginx/html/config.js`) with the Azure URLs (`https://<your-apim>.azure-api.net`, the Entra-issued token endpoint, etc.) and `liveOnboarding: false`. Same image, new environment. If your machine already uses ports `8000/8080/8081`, remap the host ports and update these URLs to match.

---

## 🔀 `liveOnboarding`: the same build, two environments

The "add a data source" wizard is the most impressive part of the demo — but it can only run where two local-only capabilities exist:

- the **registry/control-plane** has a *shared base-config volume* it can write to, and
- **Kong's admin port** is reachable so a new route can be **hot-added** (config reloaded with no restart).

In the **Azure Container Apps** deploy neither is available: each app gets one ingress port and there is no shared volume, so sources are **pre-registered** at deploy time instead of added live. Rather than letting a button error out, the app *hides* the live controls. That switch is a single config flag, read in [`src/api.js`](src/api.js):

```js
// src/api.js
export const LIVE_ONBOARDING = CFG.liveOnboarding !== false;
```

> [!IMPORTANT]
> The comparison is `!== false`, not `=== true`. That means **the wizard is shown by default** and is only hidden when config *explicitly* sets `liveOnboarding: false`. So a stripped-down `config.js` that omits the flag still gets the full local experience — only the Azure deploy, which sets it `false`, suppresses onboarding.

What the flag actually changes in the UI ([`src/App.jsx`](src/App.jsx)):

```mermaid
flowchart TD
    F{"LIVE_ONBOARDING ?"}
    F -->|true · local dev| A["Show '+ Add a data source' button<br/>Show ✕ remove on wizard-added cards<br/>Panel: 'add a source in seconds' (active voice)"]
    F -->|false · Azure deploy| B["Show 'Sources pre-registered in this deploy' note<br/>Hide remove buttons<br/>Panel: explains managed APIM/API Center equivalent"]
```

This is a clean teaching example of **graceful degradation**: instead of a feature that crashes when its dependencies are absent, the same codebase quietly adapts to what the environment supports — exactly the "services degrade gracefully, never crash on a missing dependency" rule the project follows.

---

## 🧩 Component-by-component walkthrough

The data flows top-down through a small, readable tree. There is no router and no global state library — just React state lifted into [`App.jsx`](src/App.jsx).

```mermaid
flowchart TD
    M["main.jsx<br/>mounts the app"] --> APP["App.jsx<br/>holds: catalog data, active product, wizard open?"]
    APP --> EM["Emblem.jsx<br/>SVG mission badge"]
    APP --> QC["QueryConsole.jsx<br/>opens for the clicked card"]
    APP --> WZ["AddSourceWizard.jsx<br/>opens from the CTA (live only)"]
    QC --> RT["ResultTable.jsx<br/>renders returned rows"]
    WZ -. "verifies by calling" .-> KONG["gatewayGet() → Kong"]
    QC -. "calls" .-> KONG
```

### 🚀 `main.jsx` — the entry point

Three lines of substance: create a React root on the `#root` div from `index.html` and render `<App/>` inside `<React.StrictMode>`. StrictMode is a development-only wrapper that double-invokes certain functions to surface accidental side-effects; it has no effect in the production build.

### 🏛️ `App.jsx` — the page and the source of truth

`App` owns the whole screen and the small amount of state everything else reads:

| State | Meaning |
| --- | --- |
| `data` | the catalog (`{ products: [...] }`), loaded on mount via `listCatalog()` |
| `active` | the product whose `QueryConsole` is open (or `null`) |
| `wizard` | whether the Add-Source modal is open |
| `err` | a catalog-load error message, shown in an alert region |

On mount, a `useEffect` calls `refresh()` → `listCatalog()` (an **unauthenticated** call to the catalog service — browsing the menu doesn't need a token; *ordering* the data does). Each product renders as a **card** that is a real, keyboard-operable button (`role="button"`, `tabIndex={0}`, Enter/Space handler). Cards show owner, domain, the gateway **path**, a colored **classification chip** (`Confidential`/`Sensitive`/`Routine`), and an OpenAPI link. Clicking a card sets `active`, which mounts the `QueryConsole` below the grid.

The masthead carries the brand and either the **+ Add a data source** button or the **"Sources pre-registered in this deploy"** note, chosen by `LIVE_ONBOARDING`. A persistent yellow **banner** restates the synthetic-data + zero-move message, and three explainer **panels** ("Zero-move", "Governed at the edge", "Add a source in seconds") reinforce the narrative. The **footer** prints the four configured endpoint URLs — a nice transparency touch so a viewer can see exactly where the UI is pointed.

### 🛰️ `Emblem.jsx` — original mission badge

A self-contained SVG: a deep-blue gradient disc with a red rim, a small star field, an orbit ellipse, and a trajectory swoosh with a "craft" dot. It is **original artwork, not the NASA logo** (the comment says so explicitly) — important for an agency-themed sample that must not imply endorsement. It carries `role="img"` and an `aria-label` so screen readers announce it as "mission emblem."

### 🔭 `QueryConsole.jsx` — the heart of the demo

When you click a card, this panel opens and lets you **run a query through the gateway** for that product.

- For the **Artemis supply-risk** product (`id === "artemis-supply-risk"`) it shows real query controls — *Program*, *Min avg delay (days)*, *Criticality*, *sole-source only*, and a *Consumer* selector — and builds an OData query with `supplyRiskPath(...)`.
- For **any other** source it derives a sample path from the product's `sample_url` (stripping the host) or `request_path`, so the very same console works for a source added by the wizard.

The **Consumer** selector (`analyst` vs `artemis-agent`) is a teaching device: switching it changes *which token is minted*, so you can show **per-consumer** rate-limiting and metering in Grafana. Pressing **Run through gateway** calls `gatewayGet(samplePath, consumer)` and then renders three things: the **HTTP status**, the **gateway correlation-id**, and the rows in a `ResultTable`. The results live in a container marked `aria-live="polite"` so assistive tech announces them when they arrive.

### 🛠️ `AddSourceWizard.jsx` — publish an existing API in four steps

A modal dialog (steps: **Identify → Connect → Govern → Review & publish**) pre-filled with a synthetic **DOT bridge-inventory** source. Its core lesson: you publish an *existing* API through the gateway — **the source is never modified; the gateway just learns a new upstream.** On **Publish** it `POST`s the spec to the registry (which hot-adds the Kong route), then **immediately proves it** by calling the new source's sample path through `gatewayGet` and showing the resulting status + correlation id + row count. That "publish, then prove through the gateway in the same breath" loop is the whole pitch made tangible.

It's also a tidy accessibility example: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` tied to the title, a backdrop click to close, and an **Escape-to-close** listener registered at the *document* level (the comment explains why — a keydown on a non-focusable backdrop `div` never fires, so you must listen globally while the dialog is open).

### 📊 `ResultTable.jsx` — render any rows, accessibly

Deliberately generic: it takes `rows`, reads the column names from the **first** row's keys, and renders a table — so it works for Artemis rows, DOT bridge rows, or any future source without changes. It adds an `aria-label`ed, focusable scroll region and an `sr-only` `<caption>` announcing the row count, uses `scope="col"` headers, and pretty-prints booleans as `yes`/`no`. The `renderCell` helper adds small semantic touches like coloring a `risk_tier` or a "deficient" status.

---

## 🏃 `make ui` vs `npm run dev` — two ways to run

These two commands look similar but serve **different jobs**. Knowing which to reach for is the single most common point of confusion.

| | `npm run dev` (Vite dev server) | `make ui` (Docker + nginx) |
| --- | --- | --- |
| **Purpose** | **Develop** the UI — fast feedback loop | **Demo** the UI — production-like, in the stack |
| **What runs** | Vite dev server (HMR) | Multi-stage Docker: `vite build` → nginx serves `dist/` |
| **URL** | `http://localhost:5173` | `http://localhost:${FRONTEND_PORT:-5173}` (host → container `:80`) |
| **Hot reload** | ✅ instant on save | ❌ rebuild the image to see changes |
| **`config.js` source** | `public/config.js` served by Vite | baked into the image at build, served by nginx (`no-store`) |
| **Needs the backend?** | yes, to actually fetch data (run `make up`) | yes — runs alongside it via the `frontend` Compose profile |
| **Defined in** | [`package.json`](package.json) → `"dev": "vite"` | [`Makefile`](../Makefile) → `--profile frontend up -d --build` |

The `make ui` target ([`Makefile`](../Makefile)) is exactly:

```bash
ui: ## Start the catalog UI (browser SPA at :5173)
	$(COMPOSE) --profile frontend up -d --build
	@echo "Catalog UI: http://localhost:$${FRONTEND_PORT:-5173}"
```

It activates the **`frontend` Docker Compose profile**, which builds the image from [`frontend/Dockerfile`](Dockerfile) and runs an nginx container on the `edge` network, publishing host `${FRONTEND_PORT:-5173}` → container `:80`. Because it's a *profile*, the UI is **opt-in** — a plain `make up` brings up the core platform without it.

> [!TIP]
> **Mental model:** `npm run dev` is your **workbench** (edit, save, see it instantly). `make ui` is the **showroom** (the built artifact, served like production, sitting next to the real gateway). Develop on the workbench; demo from the showroom. For either to return data, the backend must be up — start it with `make up` first.

---

## 🧪 Worked example: query Artemis-3 supply risk through the gateway

This is the canonical demo moment. We'll do it with `npm run dev` so you can also watch the network tab.

> [!NOTE]
> **Heads-up on local ports.** This walkthrough uses the defaults `8000` (Kong) and `8081` (issuer). If those ports are already taken on your machine, remap the published host ports in your `.env`/compose and update `public/config.js` to match before you start.

**Step 1 — bring up the backend.** From the repo root:

```bash
cp .env.example .env
make up
```

*What this did:* started the core platform (Postgres + Data API Builder on the locked-down `internal` network, and Kong + the identity/catalog/registry services on the `edge` network). Data is now reachable **only** through Kong.

**Step 2 — start the dev server.** From this folder:

```bash
cd frontend
npm install      # first time only
npm run dev
```

Expected output (abridged):

```text
  VITE v5.4.11  ready in 420 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

*What this did:* started Vite with hot-module reload. Open `http://localhost:5173`. The catalog grid populates from an **unauthenticated** `GET /catalog` (browsing the menu is free).

**Step 3 — run the query.** Click the **Artemis supply-risk** card. In the console, leave the defaults (`Program = Artemis-3`, `Min avg delay = 30`, `Criticality = Critical`, *sole-source only* ✓, `Consumer = analyst`) and press **Run through gateway**. The request line shows the OData path the UI built:

```text
GET /api/SupplyRisk?$filter=program eq 'Artemis-3' and avg_delay_days gt 30 and criticality eq 'Critical' and sole_source eq true&$orderby=risk_score desc
```

Under the hood, `gatewayGet` first did `POST http://localhost:8081/token` to mint an `analyst` token, then `GET http://localhost:8000/api/SupplyRisk?...` with `Authorization: Bearer <token>`.

**Expected result on screen:**

```text
HTTP 200 · gateway correlation-id: 7b1f3c9a-...-e2
```

…followed by a table of the riskiest Artemis-3 supply lines (sole-source, critical, most-delayed first). *What this proved:* the browser asked **Kong** — not a database — for the data; Kong validated the token, applied the analyst rate limit, fetched from the in-place source, and returned rows **plus a traceable correlation id**.

**Step 4 — show the negative case.** This is the most convincing part. In the browser dev-tools console, fetch Kong **without** a token:

```js
await fetch("http://localhost:8000/api/SupplyRisk").then(r => r.status)
```

**Expected output:**

```text
401
```

*What this proved:* no token → **401 before the request ever reaches a source.** Now switch the **Consumer** dropdown to `artemis-agent`, run again, and point at Grafana (`make obs`) to see traffic attributed **per consumer** — the metering story, made real.

---

## ♿ Accessibility (Section 508 / WCAG 2.1 AA)

Government-facing software must meet **Section 508**, which in practice means **WCAG 2.1 AA**. This UI was built to that bar from the start, and the work is concentrated in [`src/styles.css`](src/styles.css) and the components. Here is what's in place and *why each technique exists*:

| Technique | Where | What problem it solves |
| --- | --- | --- |
| **Skip link** ("Skip to main content") | [`index.html`](index.html) + `.skip-link` in CSS | Lets keyboard users jump past the masthead straight to `#main` instead of tabbing through everything. It's visually hidden until focused. |
| **Visible keyboard focus** | `:focus-visible { outline: 3px solid cyan }` | A clear focus ring on every interactive element so keyboard users always know where they are. |
| **Cards are real buttons** | `App.jsx` cards: `role="button"`, `tabIndex={0}`, Enter/Space handler | A clickable `<article>` would be invisible to keyboard/AT users; this makes each card focusable and operable without a mouse. |
| **`aria-label`s on icon-only controls** | remove (`✕`) buttons, the emblem, the table region | Gives screen-reader users meaningful names instead of "button" or unlabeled graphics. |
| **Live regions** | `aria-live="assertive"` on the catalog error; `aria-live="polite"` around query results | Announces async outcomes (an error, or rows arriving) without the user having to hunt for them. |
| **Accessible modal** | `AddSourceWizard`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, **Escape to close** | Identifies the wizard as a dialog, names it, and supports the expected keyboard dismissal. |
| **Semantic table** | `ResultTable`: `<caption class="sr-only">`, `scope="col"`, focusable scroll region | Screen readers announce the row count and associate headers with cells; the scrollable area is keyboard-reachable. |
| **`prefers-reduced-motion`** | CSS media query disables transitions/animations | Respects users who get motion sickness or have vestibular disorders. |
| **`.sr-only` utility** | CSS | The standard pattern for text that's available to screen readers but not shown visually (e.g. the table caption). |

> [!TIP]
> Try it without a mouse: load the page, press <kbd>Tab</kbd> once (the skip link appears), <kbd>Enter</kbd> to jump to the grid, <kbd>Tab</kbd> to a card, <kbd>Enter</kbd>/<kbd>Space</kbd> to open its console — everything is reachable and the focus ring always shows where you are.

> **Why this matters:** the enterprise story isn't just "fast and governed" — for a public-sector platform, **accessible is non-negotiable.** Shipping the demo already at 508/AA shows the pattern is production-credible, not a toy.

---

## 🩹 Gotchas & troubleshooting

> [!WARNING]
> **"Error loading catalog" banner / nothing in the grid.** The backend isn't up or the URLs in `config.js` don't match. Run `make up` from the repo root and confirm `window.APP_CONFIG.catalog` points at a reachable catalog service.

- **CORS errors in the console.** The browser calls Kong/issuer/catalog **directly** (not same-origin), so those services must send permissive CORS headers (they do in the local stack). If you remap ports or change hosts, keep `config.js` in sync with where the services actually listen.
- **Queries 401 even though you didn't expect it.** `gatewayGet` always mints and presents a token; a 401 means the issuer is down/unreachable, or the token isn't valid for that route. Check `CFG.identity` and that `make up` finished healthy.
- **The "Add a data source" button is missing.** That's by design when `liveOnboarding: false` (the Azure-style config). Set it `true` (or omit it) in `config.js` for the local wizard.
- **Edited `config.js` but the page didn't change.** In `make ui`/nginx, `config.js` is served `no-store` so it shouldn't cache — but the *built bundle* is baked at image-build time. After editing `public/config.js` for the Docker path, rebuild: `make ui` (it runs `--build`). In `npm run dev`, just save and refresh.
- **Stale `dist/`.** `dist/` is git-ignored and regenerated by `vite build`; never hand-edit it. The committed source of truth for config is `public/config.js`.

---

## 🧭 Where to next

- **The gateway it all flows through:** see the Kong configuration and zero-move proof — [`tests/test_zero_move.py`](../tests/test_zero_move.py).
- **The catalog & registry it reads:** the FastAPI services under [`services/`](../services/) (catalog, registry/control-plane, identity issuer).
- **The query language:** the OData/REST surface auto-generated by Data API Builder — see [`docs/API.md`](../docs/API.md) if present, or the OpenAPI link on each card.
- **Run the whole thing for a live audience:** [`docs/DEMO-SCRIPT.md`](../docs/DEMO-SCRIPT.md) (presenter walkthrough).
- **Deploy to Azure (the real demo):** the architecture and Azure mapping in [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) and the Bicep under [`infra/azure/`](../infra/azure/).
- **The disclaimer & data provenance:** [`docs/DISCLAIMER.md`](../docs/DISCLAIMER.md) and [`data/README.md`](../data/README.md).

---

> [!NOTE]
> **Reminder:** all figures, names, and records shown by this UI are **synthetic** sample data for a proof-of-concept — not real NASA, DOT, or any agency data. ITAR/CUI-safe.
