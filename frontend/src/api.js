// API helpers for the marketplace SPA. All data calls go THROUGH the Kong gateway.
const CFG = window.APP_CONFIG || {
  kong: "http://localhost:8000",
  identity: "http://localhost:8081",
  catalog: "http://localhost:8080",
  registry: "http://localhost:8095",
};

export const ENDPOINTS = CFG;

// Live "add/remove a source" needs the registry's shared base-config volume + Kong's
// admin port — both present locally but NOT in the Azure Container Apps deploy (one
// ingress port per app, no shared volume), where sources are pre-registered. The deploy
// sets `liveOnboarding: false` so the UI hides those controls instead of erroring.
export const LIVE_ONBOARDING = CFG.liveOnboarding !== false;

export async function getToken(consumer = "analyst") {
  const r = await fetch(`${CFG.identity}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ consumer }),
  });
  if (!r.ok) throw new Error(`identity ${r.status}`);
  return (await r.json()).access_token;
}

export async function listCatalog() {
  const r = await fetch(`${CFG.catalog}/catalog`);
  if (!r.ok) throw new Error(`catalog ${r.status}`);
  return r.json();
}

export async function listSources() {
  const r = await fetch(`${CFG.registry}/sources`);
  if (!r.ok) throw new Error(`registry ${r.status}`);
  return (await r.json()).sources || [];
}

export async function addSource(spec) {
  const r = await fetch(`${CFG.registry}/sources`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(spec),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || `registry ${r.status}`);
  return body;
}

export async function deleteSource(id) {
  const r = await fetch(`${CFG.registry}/sources/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`registry ${r.status}`);
  return r.json();
}

// GET through the gateway with a bearer token. `path` begins with '/'.
// Returns { status, rows, correlationId, raw }.
export async function gatewayGet(path, consumer = "analyst") {
  const token = await getToken(consumer);
  const r = await fetch(`${CFG.kong}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  const correlationId = r.headers.get("X-Correlation-ID");
  let raw = null;
  try {
    raw = await r.json();
  } catch {
    raw = null;
  }
  // DAB collection endpoints return { value: [...] }; by-key endpoints can return the
  // bare entity. Normalize both to a rows array so the drill-down detail isn't empty.
  const rows = Array.isArray(raw?.value)
    ? raw.value
    : raw && typeof raw === "object" && !("error" in raw)
      ? [raw]
      : [];
  return { status: r.status, rows, correlationId, raw };
}

// Is EasyAuth in front of us (Azure), and is the visitor signed in?
// /.auth/me exists only behind Azure App Service / Container Apps auth; locally it 404s.
export async function authStatus() {
  try {
    const r = await fetch("/.auth/me", { headers: { Accept: "application/json" } });
    // Gated but signed out (EasyAuth session absent/expired) -> still offer Sign in.
    if (r.status === 401 || r.status === 403) return { gated: true, signedIn: false, name: null };
    if (!r.ok) return { gated: false, signedIn: false, name: null }; // 404 / no EasyAuth = local dev
    const data = await r.json();
    const principal = Array.isArray(data) ? data[0] : data?.clientPrincipal;
    const name =
      principal?.user_id ||
      principal?.userDetails ||
      principal?.claims?.find?.((c) => /name|email|upn/i.test(c.typ))?.val ||
      null;
    return { gated: true, signedIn: !!principal, name };
  } catch {
    return { gated: false, signedIn: false, name: null }; // local dev: no EasyAuth
  }
}

// Drill-down: compose SEVERAL governed gateway calls to build a full product detail —
// material record + risk + recent purchase orders + the supplier (PO -> Vendor). Every
// hop goes through Kong with its own correlation id (advanced "nested call" pattern).
export async function materialDetail(matnr, consumer = "analyst") {
  const enc = encodeURIComponent(matnr);
  const flt = encodeURIComponent(`matnr eq '${odataLit(matnr)}'`);
  const [mat, risk, pos] = await Promise.all([
    gatewayGet(`/api/Material/matnr/${enc}`, consumer),
    gatewayGet(`/api/SupplyRisk/matnr/${enc}`, consumer),
    gatewayGet(`/api/PurchaseOrder?$filter=${flt}&$orderby=${encodeURIComponent("delay_days desc")}&$first=5`, consumer),
  ]);
  const corr = [mat.correlationId, risk.correlationId, pos.correlationId];
  let vendor = null;
  const lifnr = pos.rows?.[0]?.lifnr;
  if (lifnr != null) {
    const v = await gatewayGet(`/api/Vendor/lifnr/${lifnr}`, consumer);
    vendor = v.rows?.[0] || null;
    corr.push(v.correlationId);
  }
  return {
    material: mat.rows?.[0] || null,
    risk: risk.rows?.[0] || null,
    pos: pos.rows || [],
    vendor,
    calls: corr.filter(Boolean).length,
    correlationIds: corr.filter(Boolean),
  };
}

// Escape single quotes for an OData string literal (' -> '').
const odataLit = (s) => String(s).replace(/'/g, "''");

export function supplyRiskPath({ program, minDelay, criticality, soleSource }) {
  const clauses = [`program eq '${odataLit(program)}'`, `avg_delay_days gt ${Number(minDelay) || 0}`];
  if (criticality) clauses.push(`criticality eq '${odataLit(criticality)}'`);
  if (soleSource) clauses.push("sole_source eq true");
  const flt = clauses.join(" and ");
  return `/api/SupplyRisk?$filter=${encodeURIComponent(flt)}&$orderby=${encodeURIComponent("risk_score desc")}`;
}
