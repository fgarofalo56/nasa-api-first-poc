import { useState } from "react";
import { addSource, gatewayGet } from "../api";

// Guided 4-step "add a data source" flow. Pre-filled with the DOT transportation
// example. On publish it calls the registry, which hot-adds the route to Kong — then
// the wizard immediately proves the new source answers THROUGH the gateway.
const PRESETS = {
  dot: {
    id: "dot-bridges",
    title: "DOT Transportation — Bridge Inventory",
    upstream_url: "http://transportation:8200",
    base_path: "/dot",
    owner: "US DOT (synthetic)",
    domain: "Transportation / Infrastructure",
    classification_label: "Routine",
    require_jwt: true,
    sample_path: "/dot/api/Bridge?$orderby=condition_rating asc&$first=5",
  },
};

const STEPS = ["Identify", "Connect", "Govern", "Review & publish"];

export default function AddSourceWizard({ onDone, onClose }) {
  const [step, setStep] = useState(0);
  const [spec, setSpec] = useState(PRESETS.dot);
  const [result, setResult] = useState(null);
  const [verify, setVerify] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setSpec({ ...spec, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function publish() {
    setBusy(true);
    setError(null);
    try {
      const res = await addSource(spec);
      setResult(res);
      // prove it instantly: call the new source through the gateway
      if (spec.sample_path) {
        const probe = await gatewayGet(spec.sample_path.replace(/^https?:\/\/[^/]+/, ""));
        setVerify(probe);
      }
      setStep(4);
      onDone?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="wizard-backdrop" onClick={onClose} onKeyDown={(e) => e.key === "Escape" && onClose()}>
      <div
        className="wizard"
        role="dialog"
        aria-modal="true"
        aria-labelledby="wizard-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="wizard-head">
          <h2 id="wizard-title">Add a data source</h2>
          <button className="ghost" onClick={onClose} aria-label="Close dialog">
            ✕
          </button>
        </div>

        <ol className="steps">
          {STEPS.map((s, i) => (
            <li key={s} className={i === step ? "active" : i < step ? "done" : ""}>
              <span className="num">{i < step ? "✓" : i + 1}</span>
              {s}
            </li>
          ))}
        </ol>

        {step === 0 && (
          <div className="wstep">
            <p className="muted">
              Publish an <b>existing</b> API (e.g. a Data API Builder endpoint) through the gateway —
              the source is never modified; the gateway just learns a new upstream.
            </p>
            <label>
              Source id
              <input value={spec.id} onChange={set("id")} />
            </label>
            <label>
              Title
              <input value={spec.title} onChange={set("title")} />
            </label>
            <label>
              Domain
              <input value={spec.domain} onChange={set("domain")} />
            </label>
            <label>
              Owner
              <input value={spec.owner} onChange={set("owner")} />
            </label>
          </div>
        )}

        {step === 1 && (
          <div className="wstep">
            <label>
              Upstream URL (the existing DAB/API base)
              <input value={spec.upstream_url} onChange={set("upstream_url")} />
            </label>
            <label>
              Gateway path (where consumers reach it)
              <input value={spec.base_path} onChange={set("base_path")} />
            </label>
            <label>
              Sample query path
              <input value={spec.sample_path} onChange={set("sample_path")} />
            </label>
            <p className="muted">
              Tip: to federate the live published DOT demo, set the upstream to its
              <code> https://…azurecontainerapps.io</code> URL — everything else stays the same.
            </p>
          </div>
        )}

        {step === 2 && (
          <div className="wstep">
            <label className="check">
              <input type="checkbox" checked={spec.require_jwt} onChange={set("require_jwt")} />
              Require JWT (gateway auth) + per-consumer rate limiting
            </label>
            <label>
              Classification
              <select value={spec.classification_label} onChange={set("classification_label")}>
                <option>Routine</option>
                <option>Sensitive</option>
                <option>Confidential</option>
              </select>
            </label>
            <p className="muted">
              The same governance the Artemis source has — JWT validation, 60/min per consumer,
              correlation id, CORS — is applied to this new source automatically.
            </p>
          </div>
        )}

        {step === 3 && (
          <div className="wstep">
            <p className="muted">Review — publishing hot-reloads the gateway (no restart):</p>
            <pre className="review">{JSON.stringify(spec, null, 2)}</pre>
            {error && <div className="err">{error}</div>}
          </div>
        )}

        {step === 4 && (
          <div className="wstep">
            <div className="ok">✓ Published — <b>{spec.title}</b> is live at <code>{spec.base_path}</code> through the gateway.</div>
            {verify && (
              <>
                <div className="corr">
                  Proof: HTTP {verify.status} · correlation-id <code>{verify.correlationId || "(none)"}</code>
                </div>
                <p className="muted">{verify.rows?.length || 0} rows returned through Kong from the new source.</p>
              </>
            )}
          </div>
        )}

        <div className="wizard-nav">
          {step > 0 && step < 4 && (
            <button className="ghost" onClick={() => setStep(step - 1)}>
              Back
            </button>
          )}
          {step < 3 && (
            <button className="run" onClick={() => setStep(step + 1)}>
              Next
            </button>
          )}
          {step === 3 && (
            <button className="run" onClick={publish} disabled={busy}>
              {busy ? "Publishing…" : "Publish through gateway"}
            </button>
          )}
          {step === 4 && (
            <button className="run" onClick={onClose}>
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
