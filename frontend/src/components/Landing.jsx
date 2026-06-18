// Public landing page (shown first, before auth kicks in). Mirrors the DOT-style entry:
// a visitor lands here, reads the value prop, and chooses to sign in (Microsoft Entra)
// or explore the demo. Sign-in uses the App Service / Container Apps EasyAuth endpoint.
const LOGIN_URL = "/.auth/login/aad?post_login_redirect_uri=/";
const LOGOUT_URL = "/.auth/logout?post_logout_redirect_uri=/";
// Optional Power BI report link (the same Gold mart in BI); hidden unless config sets it.
const POWERBI_URL = (typeof window !== "undefined" && window.APP_CONFIG && window.APP_CONFIG.powerbi) || "";

const HIGHLIGHTS = [
  ["🛰️", "Zero data movement", "The system of record never moves — the gateway brokers every call."],
  ["🔐", "Governed at the edge", "Entra/JWT auth, per-consumer rate limits, an OWASP guard, field-level redaction."],
  ["🔎", "Drill-down detail", "Click any result to compose a full product record through nested governed calls."],
  ["📊", "Lakehouse + Power BI", "The same data product feeds Databricks (Unity Catalog) and Power BI — zero-move."],
];

export default function Landing({ auth, onEnter }) {
  return (
    <div className="landing">
      <div className="stars" aria-hidden />
      <main id="main" className="landing-inner">
        <img className="nasa-logo" src="/nasa-logo.svg" alt="NASA logo" width="132" height="110" />
        <p className="eyebrow">NASA OCIO · Track-A pilot · synthetic data</p>
        <h1>API-First Data Marketplace</h1>
        <p className="lede">
          An enterprise proof-of-concept of the <strong>zero-move</strong> data-marketplace pattern:
          mission data stays in its system of record, a governed gateway exposes it as an API, and
          humans, AI agents, and the analytics platform all get answers <strong>through the gateway</strong>.
          Built to deploy on <strong>Azure</strong> (API Management · Entra ID · Container Apps · Databricks);
          runs locally for dev/test.
        </p>

        <div className="landing-cta">
          {auth.gated && !auth.signedIn && (
            <a className="cta" href={LOGIN_URL}>Sign in with Microsoft</a>
          )}
          {auth.signedIn && (
            <>
              <span className="cta-note">✓ Signed in{auth.name ? ` as ${auth.name}` : ""}</span>
              <a className="cta" href="#" onClick={(e) => { e.preventDefault(); onEnter(); }}>Enter the marketplace →</a>
            </>
          )}
          <button className={auth.gated && !auth.signedIn ? "cta ghost-cta" : "cta"} onClick={onEnter}>
            Explore the demo →
          </button>
          {POWERBI_URL && (
            <a className="cta ghost-cta" href={POWERBI_URL} target="_blank" rel="noreferrer">
              📊 Power BI report ↗
            </a>
          )}
          {auth.signedIn && <a className="link-quiet" href={LOGOUT_URL}>Sign out</a>}
        </div>

        <ul className="landing-grid">
          {HIGHLIGHTS.map(([icon, title, body]) => (
            <li key={title}>
              <span className="hl-icon" aria-hidden>{icon}</span>
              <h3>{title}</h3>
              <p>{body}</p>
            </li>
          ))}
        </ul>

        <p className="banner landing-banner">
          SYNTHETIC DATA — not real NASA/DOT records. ITAR/CUI-safe. Every call is brokered,
          authenticated, rate-limited, and metered by the gateway; data never leaves its source.
        </p>
      </main>
    </div>
  );
}
