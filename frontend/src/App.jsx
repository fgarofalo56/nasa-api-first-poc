import { useEffect, useState } from "react";
import { ENDPOINTS, LIVE_ONBOARDING, authStatus, deleteSource, listCatalog } from "./api";
import Landing from "./components/Landing.jsx";
import QueryConsole from "./components/QueryConsole.jsx";
import AddSourceWizard from "./components/AddSourceWizard.jsx";
import ProductDetail from "./components/ProductDetail.jsx";

const LABEL_COLORS = { Confidential: "#fc3d21", Sensitive: "#ff9e1b", Routine: "#3ddc97" };
const LOGOUT_URL = "/.auth/logout?post_logout_redirect_uri=/";

export default function App() {
  const [data, setData] = useState({ products: [] });
  const [active, setActive] = useState(null);
  const [wizard, setWizard] = useState(false);
  const [err, setErr] = useState(null);
  const [view, setView] = useState("landing");
  const [auth, setAuth] = useState({ gated: false, signedIn: false, name: null });
  const [detail, setDetail] = useState(null); // { row, consumer }

  useEffect(() => {
    authStatus().then(setAuth);
  }, []);
  useEffect(() => {
    if (view === "app") refresh();
  }, [view]);

  async function refresh() {
    try {
      setData(await listCatalog());
    } catch (e) {
      setErr(String(e));
    }
  }

  async function removeSource(id) {
    try {
      await deleteSource(id);
      if (active?.id === id) setActive(null);
      refresh();
    } catch (e) {
      setErr(`Could not remove '${id}': ${e}`);
    }
  }

  if (view === "landing") return <Landing auth={auth} onEnter={() => setView("app")} />;

  return (
    <div className="app">
      <div className="stars" aria-hidden />
      <header className="masthead">
        <div className="brand">
          <button className="home-logo" onClick={() => setView("landing")} aria-label="Back to home">
            <img src="/nasa-logo.svg" alt="" width="64" height="53" />
          </button>
          <div>
            <div className="eyebrow">NASA OCIO · Track-A pilot · synthetic data</div>
            <h1>API-First Data Marketplace</h1>
            <p className="tagline">
              Zero-move · one governed gateway for data, APIs, and code — Microsoft as the
              interoperability layer, not "the one AI."
            </p>
          </div>
        </div>
        <div className="masthead-actions">
          {auth.signedIn && (
            <span className="who">✓ {auth.name || "signed in"} · <a href={LOGOUT_URL}>sign out</a></span>
          )}
          {LIVE_ONBOARDING ? (
            <button className="cta" onClick={() => setWizard(true)}>+ Add a data source</button>
          ) : (
            <span className="cta-note" title="Live onboarding runs in local dev; in this Azure deploy, sources are pre-registered">
              Sources pre-registered in this deploy
            </span>
          )}
        </div>
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
            <h2 id="mkt-heading">
              Marketplace · {data.products.length} data product{data.products.length === 1 ? "" : "s"}
            </h2>
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
                  {LIVE_ONBOARDING && p.origin?.includes("wizard") && (
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
            <QueryConsole
              product={active}
              onClose={() => setActive(null)}
              onOpenDetail={(row, consumer) => setDetail({ row, consumer })}
            />
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
            <h3>🔎 Drill-down detail</h3>
            <p>
              Click any result row to compose a full product record — material, risk, purchase
              orders, and supplier — through several nested governed gateway calls.
            </p>
          </div>
        </section>
      </main>

      <footer>
        <span>Gateway {ENDPOINTS.kong}</span> · <span>Identity {ENDPOINTS.identity}</span> ·{" "}
        <span>Catalog {ENDPOINTS.catalog}</span> · <span>Registry {ENDPOINTS.registry}</span>
      </footer>

      {wizard && <AddSourceWizard onClose={() => setWizard(false)} onDone={refresh} />}
      {detail && <ProductDetail row={detail.row} consumer={detail.consumer} onClose={() => setDetail(null)} />}
    </div>
  );
}
