import { useState } from "react";
import { gatewayGet, supplyRiskPath } from "../api";
import ResultTable from "./ResultTable.jsx";

// Query a selected source THROUGH the gateway. The Artemis source gets parametric
// controls; every source can run its catalog sample query. Shows the correlation id.
export default function QueryConsole({ product, onClose }) {
  const isArtemis = product.id === "artemis-supply-risk";
  const [program, setProgram] = useState("Artemis-3");
  const [minDelay, setMinDelay] = useState(30);
  const [criticality, setCriticality] = useState("Critical");
  const [soleSource, setSoleSource] = useState(true);
  const [consumer, setConsumer] = useState("analyst");
  const [state, setState] = useState({ loading: false });

  const samplePath = (() => {
    if (isArtemis) return supplyRiskPath({ program, minDelay, criticality, soleSource });
    // dynamic source: derive a gateway path from sample_url or request_path
    if (product.sample_url) return product.sample_url.replace(/^https?:\/\/[^/]+/, "");
    return `${product.request_path}/api/openapi`;
  })();

  async function run() {
    setState({ loading: true });
    try {
      const res = await gatewayGet(samplePath, consumer);
      setState({ loading: false, ...res });
    } catch (e) {
      setState({ loading: false, error: String(e) });
    }
  }

  return (
    <div className="console">
      <div className="console-head">
        <h3>Query · {product.title}</h3>
        <button className="ghost" onClick={onClose}>
          close
        </button>
      </div>

      {isArtemis ? (
        <div className="form">
          <label>
            Program
            <input value={program} onChange={(e) => setProgram(e.target.value)} />
          </label>
          <label>
            Min avg delay (days)
            <input type="number" value={minDelay} onChange={(e) => setMinDelay(Number(e.target.value))} />
          </label>
          <label>
            Criticality
            <select value={criticality} onChange={(e) => setCriticality(e.target.value)}>
              <option value="Critical">Critical</option>
              <option value="Essential">Essential</option>
              <option value="Routine">Routine</option>
              <option value="">(any)</option>
            </select>
          </label>
          <label className="check">
            <input type="checkbox" checked={soleSource} onChange={(e) => setSoleSource(e.target.checked)} />
            sole-source only
          </label>
          <label>
            Consumer
            <select value={consumer} onChange={(e) => setConsumer(e.target.value)}>
              <option value="analyst">analyst</option>
              <option value="artemis-agent">artemis-agent</option>
            </select>
          </label>
        </div>
      ) : (
        <p className="muted">
          Runs this source's sample query through the gateway as <code>{consumer}</code>.
        </p>
      )}

      <div className="req"><span className="k">GET</span><code>{samplePath}</code></div>
      <button className="run" onClick={run} disabled={state.loading}>
        {state.loading ? "Querying…" : "Run through gateway"}
      </button>

      <div aria-live="polite">
        {state.error && <div className="err" role="alert">Error: {state.error}</div>}
        {state.status != null && (
          <div className="corr">
            HTTP {state.status} · gateway correlation-id: <code>{state.correlationId || "(none)"}</code>
          </div>
        )}
        {state.rows && <ResultTable rows={state.rows} />}
      </div>
    </div>
  );
}
