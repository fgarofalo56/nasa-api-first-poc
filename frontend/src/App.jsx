import { useEffect, useState } from "react";

const CFG = window.APP_CONFIG || {
  kong: "http://localhost:8000",
  identity: "http://localhost:8081",
  catalog: "http://localhost:8080",
};

async function getToken(consumer) {
  const r = await fetch(`${CFG.identity}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ consumer }),
  });
  if (!r.ok) throw new Error(`identity ${r.status}`);
  return (await r.json()).access_token;
}

function buildFilter(program, minDelay, criticality, soleSource) {
  const c = [`program eq '${program}'`, `avg_delay_days gt ${minDelay}`];
  if (criticality) c.push(`criticality eq '${criticality}'`);
  if (soleSource) c.push("sole_source eq true");
  return c.join(" and ");
}

const LABEL_COLORS = { Confidential: "#cf222e", Sensitive: "#bc4c00", Routine: "#1a7f37" };

function ClassificationChips({ classification }) {
  if (!classification?.tables) return null;
  return (
    <div className="chips">
      {Object.entries(classification.tables).map(([t, label]) => (
        <span key={t} className="chip" style={{ borderColor: LABEL_COLORS[label] || "#888" }}>
          <b>{t}</b>: <span style={{ color: LABEL_COLORS[label] || "#444" }}>{label}</span>
        </span>
      ))}
    </div>
  );
}

export default function App() {
  const [product, setProduct] = useState(null);
  const [program, setProgram] = useState("Artemis-3");
  const [minDelay, setMinDelay] = useState(30);
  const [consumer, setConsumer] = useState("analyst");
  const [criticality, setCriticality] = useState("Critical");
  const [soleSource, setSoleSource] = useState(true);
  const [rows, setRows] = useState(null);
  const [corr, setCorr] = useState(null);
  const [status, setStatus] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const [openapi, setOpenapi] = useState(null);

  useEffect(() => {
    fetch(`${CFG.catalog}/catalog/artemis-supply-risk`)
      .then((r) => r.json())
      .then(setProduct)
      .catch((e) => setErr(`catalog: ${e}`));
  }, []);

  async function run() {
    setErr(null);
    setLoading(true);
    setRows(null);
    setCorr(null);
    setStatus(null);
    try {
      const token = await getToken(consumer);
      const flt = buildFilter(program, minDelay, criticality, soleSource);
      const url = `${CFG.kong}/api/SupplyRisk?$filter=${encodeURIComponent(
        flt,
      )}&$orderby=${encodeURIComponent("risk_score desc")}`;
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      setStatus(r.status);
      setCorr(r.headers.get("X-Correlation-ID"));
      if (!r.ok) throw new Error(`gateway returned HTTP ${r.status}`);
      const data = await r.json();
      setRows(data.value || []);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function loadOpenApi() {
    setErr(null);
    try {
      const r = await fetch(`${CFG.kong}/api/openapi`);
      const spec = await r.json();
      setOpenapi(Object.keys(spec.paths || {}).sort());
    } catch (e) {
      setErr(`openapi: ${e}`);
    }
  }

  return (
    <div className="wrap">
      <header>
        <h1>Artemis Data Marketplace</h1>
        <p className="sub">
          API-first, zero-move demo &mdash; every call is brokered through the gateway.
        </p>
        <div className="banner">SYNTHETIC DATA &mdash; not real NASA procurement. ITAR/CUI-safe.</div>
      </header>

      {product && (
        <section className="card">
          <h2>{product.title}</h2>
          <p>{product.description}</p>
          <div className="meta">
            <div><span className="k">Owner</span>{product.owner}</div>
            <div><span className="k">Domain</span>{product.domain}</div>
            <div><span className="k">Request path</span><code>{product.request_path}</code></div>
            <div>
              <span className="k">OpenAPI</span>
              <a href={product.openapi_url} target="_blank" rel="noreferrer">{product.openapi_url}</a>
            </div>
            <div><span className="k">Auth</span>{product.auth}</div>
            <div><span className="k">Rate limit</span>{product.rate_limit_per_minute}/min per consumer</div>
          </div>
          <h3>Classification (classify-before-exposure)</h3>
          <ClassificationChips classification={product.classification} />
          <button className="link" onClick={loadOpenApi}>Show OpenAPI paths</button>
          {openapi && (
            <ul className="paths">
              {openapi.map((p) => (
                <li key={p}><code>{p}</code></li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="card">
        <h2>Run the supply-risk query (through Kong)</h2>
        <div className="form">
          <label>Program
            <input value={program} onChange={(e) => setProgram(e.target.value)} />
          </label>
          <label>Min avg delay (days)
            <input type="number" value={minDelay} onChange={(e) => setMinDelay(Number(e.target.value))} />
          </label>
          <label>Criticality
            <select value={criticality} onChange={(e) => setCriticality(e.target.value)}>
              <option value="Critical">Critical</option>
              <option value="Essential">Essential</option>
              <option value="Routine">Routine</option>
              <option value="">(any)</option>
            </select>
          </label>
          <label>Consumer
            <select value={consumer} onChange={(e) => setConsumer(e.target.value)}>
              <option value="analyst">analyst</option>
              <option value="artemis-agent">artemis-agent</option>
            </select>
          </label>
          <label className="check">
            <input type="checkbox" checked={soleSource} onChange={(e) => setSoleSource(e.target.checked)} />
            sole-source only
          </label>
          <button className="run" onClick={run} disabled={loading}>
            {loading ? "Querying…" : "Run through gateway"}
          </button>
        </div>

        {err && <div className="err">Error: {err}</div>}
        {status != null && (
          <div className="corr">
            HTTP {status} &middot; gateway correlation-id: <code>{corr || "(none)"}</code>
          </div>
        )}
        {rows && (
          rows.length ? (
            <table>
              <thead>
                <tr><th>Tier</th><th>Risk</th><th>Avg delay</th><th>Material</th><th>Criticality</th><th>Sole-source</th></tr>
              </thead>
              <tbody>
                {rows.map((m) => (
                  <tr key={m.matnr}>
                    <td><span className={`tier ${m.risk_tier?.toLowerCase()}`}>{m.risk_tier}</span></td>
                    <td>{m.risk_score}</td>
                    <td>{Number(m.avg_delay_days).toFixed(1)}</td>
                    <td>{m.maktx}</td>
                    <td>{m.criticality}</td>
                    <td>{m.sole_source ? "yes" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty">No materials matched. Try min delay 0 or uncheck sole-source.</div>
          )
        )}
      </section>

      <footer>Data never leaves Postgres &mdash; brokered, authenticated, rate-limited, and metered by Kong.</footer>
    </div>
  );
}
