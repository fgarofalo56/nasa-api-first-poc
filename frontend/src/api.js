// API helpers for the marketplace SPA. All data calls go THROUGH the Kong gateway.
const CFG = window.APP_CONFIG || {
  kong: "http://localhost:8000",
  identity: "http://localhost:8081",
  catalog: "http://localhost:8080",
  registry: "http://localhost:8095",
};

export const ENDPOINTS = CFG;

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
  return { status: r.status, rows: raw?.value || [], correlationId, raw };
}

export function supplyRiskPath({ program, minDelay, criticality, soleSource }) {
  const clauses = [`program eq '${program}'`, `avg_delay_days gt ${minDelay}`];
  if (criticality) clauses.push(`criticality eq '${criticality}'`);
  if (soleSource) clauses.push("sole_source eq true");
  const flt = clauses.join(" and ");
  return `/api/SupplyRisk?$filter=${encodeURIComponent(flt)}&$orderby=${encodeURIComponent("risk_score desc")}`;
}
