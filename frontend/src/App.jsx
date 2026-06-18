import { useEffect, useState } from "react";
import { ENDPOINTS, deleteSource, listCatalog } from "./api";
import Emblem from "./components/Emblem.jsx";
import QueryConsole from "./components/QueryConsole.jsx";
import AddSourceWizard from "./components/AddSourceWizard.jsx";

const LABEL_COLORS = { Confidential: "#fc3d21", Sensitive: "#ff9e1b", Routine: "#3ddc97" };

export default function App() {
  const [data, setData] = useState({ products: [] });
  const [active, setActive] = useState(null);
  const [wizard, setWizard] = useState(false);
  const [err, setErr] = useState(null);

  async function refresh() {
    try {
      setData(await listCatalog());
    } catch (e) {
      setErr(String(e));
    }
  }
  useEffect(() => {
    refresh();
  }, []);

  async function removeSource(id) {
    await deleteSource(id);
    if (active?.id === id) setActive(null);
    refresh();
  }

  return (
    <div className="app">
      <div className="stars" aria-hidden />
      <header className="masthead">
        <div className="brand">
          <Emblem size={58} />
          <div>
            <div className="eyebrow">NASA OCIO · Track-A pilot · synthetic data</div>
            <h1>API-First Data Marketplace</h1>
            <p className="tagline">
              Zero-move · one governed gateway for data, APIs, and code — Microsoft as the
              interoperability layer, not "the one AI."
            </p>
          </div>
        </div>
        <button className="cta" onClick={() => setWizard(true)}>
          + Add a data source
        </button>
      </header>

      <div className="banner">
        SYNTHETIC DATA — not real NASA/DOT records. ITAR/CUI-safe. Every call is brokered,
        authenticated, rate-limited, and metered by the gateway; data never leaves its source.
      </div>

      {err && (
        <div className="err wide" role="alert" aria-live="assertive">
          Error loading catalog: {err}
        </div>
      )}

      <main id="main">
      <section aria-labelledby="mkt-heading">
        <div className="section-head">
          <h2 id="mkt-heading">Marketplace · {data.products.length} data product{data.products.length === 1 ? "" : "s"}</h2>
          <span className="hint">Click a card to query it through the gateway.</span>
        </div>
        <div className="grid">
          {data.products.map((p) => (
            <article
              key={p.id}
              className={`card${active?.id === p.id ? " sel" : ""}`}
              role="button"
              tabIndex={0}
              aria-label={`Query ${p.title} through the gateway`}
              onClick={() => setActive(p)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setActive(p);
                }
              }}
            >
              <div className="card-top">
                <span className={`origin ${p.origin?.includes("wizard") ? "added" : "builtin"}`}>
                  {p.origin?.includes("wizard") ? "added via wizard" : "built-in"}
                </span>
                {p.origin?.includes("wizard") && (
                  <button
                    className="trash"
                    title="remove source"
                    aria-label={`Remove source ${p.title}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      removeSource(p.id);
                    }}
                  >
                    ✕
                  </button>
                )}
              </div>
              <h3>{p.title}</h3>
              <div className="kv"><span>Owner</span>{p.owner}</div>
              <div className="kv"><span>Domain</span>{p.domain}</div>
              <div className="kv"><span>Path</span><code>{p.request_path}</code></div>
              {p.classification_label && (
                <span className="chip" style={{ borderColor: LABEL_COLORS[p.classification_label] }}>
                  {p.classification_label}
                </span>
              )}
              {p.openapi_url && (
                <a className="oa" href={p.openapi_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
                  OpenAPI ↗
                </a>
              )}
            </article>
          ))}
        </div>
      </section>

      {active && (
        <section>
          <QueryConsole product={active} onClose={() => setActive(null)} />
        </section>
      )}

      <section className="panels">
        <div className="panel">
          <h3>🛰️ Zero-move</h3>
          <p>
            Sources (Postgres, DAB, the DOT API) sit on an internal network with no public ports.
            The only path to data is the gateway — proven by the test suite.
          </p>
        </div>
        <div className="panel">
          <h3>🔐 Governed at the edge</h3>
          <p>
            JWT validated (RS256, Entra-pattern), per-consumer rate limits, an OWASP guard, and a
            correlation id on every call. No token → 401 before the request reaches a source.
          </p>
        </div>
        <div className="panel">
          <h3>➕ Add a source in seconds</h3>
          <p>
            The wizard publishes any existing API through the gateway with a live config reload —
            no source change, no downtime. This is the APIM / API Center pattern, locally.
          </p>
        </div>
      </section>
      </main>

      <footer>
        <span>Gateway {ENDPOINTS.kong}</span> · <span>Identity {ENDPOINTS.identity}</span> ·{" "}
        <span>Catalog {ENDPOINTS.catalog}</span> · <span>Registry {ENDPOINTS.registry}</span>
      </footer>

      {wizard && <AddSourceWizard onClose={() => setWizard(false)} onDone={refresh} />}
    </div>
  );
}
