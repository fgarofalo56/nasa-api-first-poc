import { useEffect, useRef, useState } from "react";
import { materialDetail } from "../api.js";
import { labelFor, productImageSrc } from "../labels.js";

// Drill-down detail for one material. Opening it fires SEVERAL governed gateway calls
// (material -> risk -> purchase orders -> supplier) and shows the assembled product
// record + a blueprint visual. Demonstrates an advanced nested/composed API pattern,
// every hop authenticated + correlation-id'd by the gateway.
export default function ProductDetail({ row, consumer, onClose }) {
  const matnr = row?.matnr;
  const [state, setState] = useState({ loading: true });
  const [imgFailed, setImgFailed] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    let live = true;
    setState({ loading: true });
    setImgFailed(false);
    materialDetail(matnr, consumer)
      .then((d) => live && setState({ loading: false, ...d }))
      .catch((e) => live && setState({ loading: false, error: String(e) }));
    return () => {
      live = false;
    };
  }, [matnr, consumer]);

  // Modal a11y: close on Escape, move focus into the dialog, restore focus on close.
  useEffect(() => {
    const prev = document.activeElement;
    const onKey = (e) => e.key === "Escape" && onClose?.();
    document.addEventListener("keydown", onKey);
    ref.current?.querySelector("button")?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      prev?.focus?.();
    };
  }, [onClose]);

  const m = state.material || {};
  const r = state.risk || {};
  const v = state.vendor;
  const pos = state.pos || [];
  const corr = state.correlationIds || [];
  // Blueprint is keyed by the material NAME (24 distinct), not the unique NSN matnr.
  const imgSrc = productImageSrc(m.maktx || row?.maktx);

  return (
    <div className="detail-backdrop" onClick={onClose}>
      <aside
        ref={ref}
        className="detail"
        role="dialog"
        aria-modal="true"
        aria-label={`Details for ${row?.maktx || matnr}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="detail-head">
          <div>
            <div className="eyebrow">{m.matkl || row?.matkl || "Material"} · {m.program || row?.program}</div>
            <h2>{m.maktx || row?.maktx || matnr}</h2>
            <code className="muted">{matnr}</code>
          </div>
          <button className="ghost" onClick={onClose} aria-label="Close details">✕</button>
        </div>

        <div aria-live="polite">
          {state.loading && <div className="detail-loading">Composing the full record through the gateway…</div>}
          {state.error && <div className="err" role="alert">Error: {state.error}</div>}

          {!state.loading && !state.error && (
            <div className="detail-body">
              <figure className="blueprint">
                {!imgFailed && imgSrc ? (
                  <img
                    src={imgSrc}
                    alt={`Engineering render of ${m.maktx || matnr}`}
                    onError={() => setImgFailed(true)}
                  />
                ) : (
                  <div className="blueprint-fallback">
                    <BlueprintGlyph family={m.matkl || row?.matkl} />
                    <figcaption>Blueprint · {m.matkl || "component"} (synthetic)</figcaption>
                  </div>
                )}
              </figure>

              {r.risk_tier && (
                <div className={`risk-banner tier ${String(r.risk_tier).toLowerCase()}`}>
                  <strong>{r.risk_tier} risk</strong> · score {r.risk_score} ·{" "}
                  avg delay {Number(r.avg_delay_days).toFixed(1)} days
                  {r.sole_source ? " · sole-source" : ""}
                </div>
              )}

              <Section title="Material">
                <Facts obj={m} keys={["matkl", "program", "criticality", "std_lead_time_days", "uom"]} />
              </Section>

              {v && (
                <Section title="Supplier">
                  <Facts obj={v} keys={["name1", "cage_code", "past_perf_score", "small_business", "sole_source"]} />
                </Section>
              )}

              <Section title={`Recent purchase orders (${pos.length})`}>
                {pos.length === 0 ? (
                  <p className="muted">No purchase orders returned.</p>
                ) : (
                  <div className="mini-wrap">
                    <table className="mini">
                      <thead>
                        <tr>{["ebeln", "menge", "eindt", "actual_delivery", "delay_days", "status"].map((c) => (
                          <th key={c}>{labelFor(c)}</th>
                        ))}</tr>
                      </thead>
                      <tbody>
                        {pos.map((p, i) => (
                          <tr key={p.ebeln || i}>
                            <td>{p.ebeln}</td>
                            <td>{p.menge}</td>
                            <td>{p.eindt}</td>
                            <td>{p.actual_delivery || "—"}</td>
                            <td>{p.delay_days}</td>
                            <td>{/deficient/i.test(String(p.status)) ? <span className="tier high">{p.status}</span> : p.status}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Section>

              <div className="detail-foot">
                🛡️ Assembled from <strong>{state.calls}</strong> governed gateway calls (Material → SupplyRisk →
                PurchaseOrder → Vendor). Net price/value and unit cost are <em>redacted at the gateway</em> — the
                same field-level governance every consumer gets. Correlation ids:{" "}
                <code>{corr.join(", ") || "(none)"}</code>
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="detail-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function Facts({ obj, keys }) {
  return (
    <dl className="facts">
      {keys
        .filter((k) => obj[k] !== undefined && obj[k] !== null)
        .map((k) => (
          <div key={k}>
            <dt>{labelFor(k)}</dt>
            <dd>{typeof obj[k] === "boolean" ? (obj[k] ? "yes" : "no") : String(obj[k])}</dd>
          </div>
        ))}
    </dl>
  );
}

// Lightweight inline "blueprint" glyph keyed off the material family — the ultimate
// fallback when /img/products/<name-slug>.svg is missing or fails to load.
function BlueprintGlyph({ family }) {
  return (
    <svg viewBox="0 0 120 90" width="160" height="120" role="img" aria-label={`${family || "component"} schematic`}>
      <rect x="0" y="0" width="120" height="90" fill="#0a1f4d" />
      <g stroke="#50e6ff" strokeWidth="0.4" opacity="0.35">
        {[...Array(12)].map((_, i) => <line key={`v${i}`} x1={i * 10} y1="0" x2={i * 10} y2="90" />)}
        {[...Array(9)].map((_, i) => <line key={`h${i}`} x1="0" y1={i * 10} x2="120" y2={i * 10} />)}
      </g>
      <circle cx="60" cy="45" r="26" fill="none" stroke="#fff" strokeWidth="1.2" />
      <circle cx="60" cy="45" r="14" fill="none" stroke="#fc3d21" strokeWidth="1.2" />
      <line x1="60" y1="6" x2="60" y2="84" stroke="#fff" strokeWidth="0.6" opacity="0.7" />
      <line x1="14" y1="45" x2="106" y2="45" stroke="#fff" strokeWidth="0.6" opacity="0.7" />
    </svg>
  );
}
