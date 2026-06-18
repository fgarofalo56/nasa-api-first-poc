# Demo script (~10 minutes)

[Home](../README.md) > [Documentation](README.md) > **Demo Script**

> [!NOTE]
> **TL;DR** — A top-to-bottom presenter script for a ~10-minute live demo: one command
> (`make demo`) brings the stack up, the mission supply-risk answer is returned through
> Kong, auth is shown (401/200/429), zero-move is proven by test, then discovery, MCP,
> observability, live source onboarding, and the Azure swap.

A presenter can follow this top to bottom for a live, screen-recordable demo of the
API-first **zero-move** pattern on synthetic Artemis SAP-procurement data. Total time
~10 minutes. Everything runs locally; nothing touches a real Azure subscription.

> [!IMPORTANT]
> **Frame (say this first):** "One platform for data, APIs, and code — Microsoft as the
> secure interoperability layer, not 'the one AI.' The data never moves; an open-source
> gateway governs an auto-generated API in front of it; an agent answers a real Artemis
> supply-chain question through that gateway."

## 🚀 0. Prerequisites (before the room)

- Docker Desktop running. Python 3.11+ on the host (for the client + MCP smoke).
- `cp .env.example .env`
- `pip install -e .` (or `pip install httpx "pyjwt[crypto]" pyyaml "mcp>=1.9,<2"`)
- Pre-pull images so the live demo is fast: `docker compose --profile core --profile observability pull`

## ⌨️ 1. One command brings the whole stack up (2 min)

```bash
make demo
```

This runs: `docker compose --profile core up -d` → wait-for-healthy → seed the synthetic
data → run the governed client → run the MCP agent smoke. Narrate while it builds:

- **Postgres** is the system of record (synthetic SAP tables: vendors, materials,
  purchase orders, derived supply risk).
- **Data API Builder** auto-generates REST + GraphQL + OpenAPI over it — *no
  hand-written API*.
- **Kong** (OSS, DB-less) fronts DAB with JWT auth, rate-limiting, per-consumer
  metering, a correlation id, and one OWASP API control.
- **Identity** issues RS256 tokens (stands in for Entra ID) and hands Kong the public key.
- **Catalog** publishes the data product; **Prometheus/Grafana** show traffic.

## 💡 2. The mission answer — through the gateway (2 min)

The `make demo` output already shows it; re-run it live to narrate:

```bash
python client/query_supply_risk.py --program Artemis-3 --min-delay 30
```

> "Which Critical, sole-source materials on Artemis-3 have an average delay > 30 days?"

Point out in the output:
- the **ranked high-risk parts** (top tier, risk ~100, multi-week average slips — e.g.
  *Heat-pipe radiator panel*, *Li-ion battery module*) and **their suppliers** (resolved
  via a second governed call: PurchaseOrder → Vendor);
- the **gateway correlation id** — proof the answer came *through Kong*, not the DB;
- the closing line: *data never left Postgres*.

## 🔒 3. Auth at the edge — 401 / 200 / 429 (2 min)

```bash
# No token -> rejected at the edge; the request never reaches DAB
curl -i http://localhost:8000/api/SupplyRisk        # 401

# Valid token -> 200 (and a correlation id header)
TOKEN=$(curl -s -X POST http://localhost:8081/token -H 'Content-Type: application/json' \
  -d '{"consumer":"analyst"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -i -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/Material?\$first=1"   # 200

# Over the rate cap -> 429 + Retry-After (fast burst)
for i in $(seq 1 80); do curl -s -o /dev/null -w "%{http_code} " \
  -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/Material?\$first=1"; done; echo

# OWASP API4 guard: an over-broad extraction is blocked at the gateway
curl -i -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/Material?\$first=99999"  # 400
```

## 🧪 4. Prove zero-move (1 min)

```bash
make test     # runs the suite, including test_zero_move.py
```

Narrate: Postgres and DAB are on an **internal** Docker network with **no host ports**;
a container on the client (`edge`) network cannot even resolve/reach them; the only path
to the data is Kong. The test asserts exactly that.

## 🔌 5. Discovery — the catalog + OpenAPI (1 min)

```bash
curl -s http://localhost:8080/catalog | python -m json.tool
curl -s http://localhost:8080/catalog/artemis-supply-risk | python -m json.tool   # owner, classification, request path, sample query
curl -s http://localhost:8000/api/openapi | python -m json.tool | head -40        # public contract (no token)
```

Point out the **classification** block (Confidential `NETPR`, Sensitive `SOLE_SOURCE`, …)
— classified *before* exposure, surfaced from `data/classification.yml`.

## 🤝 6. The agent path — MCP (1 min)

```bash
python services/mcp/smoke_client.py
```

> "An MCP agent (Claude Desktop, Copilot, Foundry) calls the same governed surface and
> gets the same answer — over the open MCP standard, never touching the database."

## 📊 7. Observability — per-consumer traffic (1 min)

```bash
make obs      # starts Prometheus + Grafana
```

Open Grafana at <http://localhost:3000> (anonymous viewer enabled) → dashboard
**"Artemis Gateway — per-consumer traffic & latency."** Re-run the client / a burst and
watch the **per-consumer request count** and **p50/p95 latency** panels update. This is
the metering story: usage attributed to `analyst` vs `artemis-agent`.

## ✨ 7b. Add a source, live — the onboarding wizard (1–2 min)

This is the "how easy is it to onboard a new data product?" moment.

```bash
make ui            # browser catalog UI at http://localhost:5173
```

In the UI: **“+ Add a data source”** → step through (pre-filled with the DOT
transportation DAB example) → **Publish through gateway.** Narrate:

- The wizard calls the **registry**, which **hot-reloads Kong** (no restart) to add the
  new upstream — the source itself is never touched.
- It instantly proves the new source answers **through Kong**: HTTP 200, a gateway
  correlation id, and rows returned.
- The new product appears in the marketplace and is queryable like any other, with the
  **same governance** (JWT, rate-limit, correlation id).

> "Onboarding a data product is registering its API with the gateway — minutes, not a
> migration. The same step maps to publishing an API in Azure API Management / API
> Center." (Full guide + the real-DOT-URL swap: `docs/ADD-A-SOURCE.md`.)

## 🌐 8. Close — the Azure swap (30 sec)

> "Same pattern promotes to Azure Government by swapping each OSS component for its
> managed equivalent — Kong → **API Management**, the issuer → **Microsoft Entra ID**,
> DAB → **DAB on Container Apps / Dataverse**, classification → **Microsoft Purview**,
> Prometheus/Grafana → **Azure Monitor** — see `docs/AZURE-DEPLOYMENT.md` and the Bicep
> under `infra/azure/`. Live, dated Azure prices: `make pricing`."

## Teardown

```bash
make down     # stops everything and removes volumes
```
