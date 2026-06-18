import { useEffect, useRef, useState } from "react";
import { askAgent } from "../api.js";
import { labelFor } from "../labels.js";

const TIER_COLOR = { high: "#fc3d21", medium: "#ff9e1b", low: "#3ddc97" };
const SUGGESTIONS = [
  "What's at risk on Artemis-3?",
  "Show me risk stats by tier",
  "Tell me about the Li-ion battery module",
  "Who supplies the heat-pipe radiator panel?",
  "What's the weather on Mars?",
];

// Grounded mission-agent chat. Sends NL questions to the agent service (which calls the
// MCP server -> gateway) and renders the structured response: text, material cards, a
// bar chart for stats, or a full detail card — each with its data source cited.
export default function AgentChat({ onOpenDetail }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([
    { role: "agent", answer: "🚀 Mission agent online. I answer Artemis supply-chain questions from the **governed data** — through the gateway, over MCP. Ask away (or try a suggestion)." },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, open]);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", answer: q }]);
    setBusy(true);
    try {
      const res = await askAgent(q);
      setMsgs((m) => [...m, { role: "agent", ...res }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "agent", answer: `🛠️ I couldn't reach the agent (${e}). Is the stack up?` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button className="agent-fab" onClick={() => setOpen((o) => !o)} aria-label="Open the mission agent">
        {open ? "✕" : "🚀 Ask the mission agent"}
      </button>

      {open && (
        <section className="agent-panel" role="dialog" aria-label="Mission agent chat">
          <header className="agent-head">
            <span>🛰️ Artemis Mission Agent</span>
            <span className="agent-badge" title="Answers only from governed gateway data via MCP">grounded · MCP</span>
          </header>

          <div className="agent-log" aria-live="polite">
            {msgs.map((m, i) => (
              <div key={i} className={`agent-msg ${m.role}`}>
                <Markdown text={m.answer} />
                {m.render?.kind === "materials" && (
                  <>
                    {m.render.chart && <BarChart chart={m.render.chart} />}
                    <div className="agent-cards">
                      {m.render.items.map((it) => (
                        <button key={it.matnr} className="agent-card" onClick={() => onOpenDetail?.(it, "artemis-agent")}>
                          <span className={`tier ${String(it.risk_tier).toLowerCase()}`}>{it.risk_tier}</span>
                          <strong>{it.maktx}</strong>
                          <span className="agent-card-meta">
                            score {it.risk_score} · {Number(it.avg_delay_days).toFixed(0)}d{it.sole_source ? " · sole-source" : ""}
                          </span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
                {m.render?.kind === "detail" && <DetailCard d={m.render} onOpen={() => onOpenDetail?.(m.render.material, "artemis-agent")} />}
                {m.sources?.length > 0 && (
                  <div className="agent-src">
                    🔗 Source: {m.sources.map((s, j) => (
                      <span key={j}>
                        MCP <code>{s.tool}</code>
                        {s.gateway_correlation_id ? <> · gw <code>{s.gateway_correlation_id}</code></> : null}
                        {j < m.sources.length - 1 ? "; " : ""}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {busy && <div className="agent-msg agent"><span className="agent-typing">querying the gateway…</span></div>}
            <div ref={endRef} />
          </div>

          <div className="agent-suggestions">
            {SUGGESTIONS.map((s) => (
              <button key={s} className="chip-btn" onClick={() => send(s)} disabled={busy}>{s}</button>
            ))}
          </div>

          <form className="agent-input" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about Artemis supply-chain risk…"
              aria-label="Ask the mission agent"
            />
            <button className="run" type="submit" disabled={busy || !input.trim()}>Send</button>
          </form>
        </section>
      )}
    </>
  );
}

// Minimal markdown: **bold** + line breaks. (Agent text is trusted, server-authored.)
function Markdown({ text }) {
  if (!text) return null;
  return (
    <div className="agent-text">
      {String(text).split("\n").map((line, i) => (
        <p key={i}>
          {line.split(/(\*\*[^*]+\*\*)/g).map((seg, j) =>
            /^\*\*[^*]+\*\*$/.test(seg) ? <strong key={j}>{seg.slice(2, -2)}</strong> : seg
          )}
        </p>
      ))}
    </div>
  );
}

function BarChart({ chart }) {
  const pts = chart.points || [];
  if (!pts.length) return null;
  const max = Math.max(...pts.map((p) => p.value), 1);
  return (
    <figure className="agent-chart">
      <figcaption>{chart.title}</figcaption>
      {pts.map((p, i) => (
        <div className="bar-row" key={i}>
          <span className="bar-label" title={p.label}>{p.label}</span>
          <span className="bar-track">
            <span
              className="bar-fill"
              style={{ width: `${(p.value / max) * 100}%`, background: TIER_COLOR[String(p.tier).toLowerCase()] || "#50e6ff" }}
            />
          </span>
          <span className="bar-val">{p.value}</span>
        </div>
      ))}
    </figure>
  );
}

function DetailCard({ d, onOpen }) {
  const m = d.material || {};
  const [imgFailed, setImgFailed] = useState(false);
  return (
    <button className="agent-detail" onClick={onOpen} aria-label={`Open full details for ${m.maktx}`}>
      {!imgFailed ? (
        <img src={d.image} alt={`Render of ${m.maktx}`} onError={() => setImgFailed(true)} />
      ) : (
        <div className="agent-detail-img-fallback" aria-hidden>🛰️</div>
      )}
      <div className="agent-detail-body">
        <span className={`tier ${String(m.risk_tier).toLowerCase()}`}>{m.risk_tier} · {m.risk_score}</span>
        <strong>{m.maktx}</strong>
        <span className="agent-card-meta">{m.program} · {m.criticality}{m.sole_source ? " · sole-source" : ""}</span>
        {m.supplier && <span className="agent-card-meta">Supplier: {m.supplier} (CAGE {m.cage_code || "?"})</span>}
        <span className="agent-card-meta">{(d.recent_pos || []).length} recent POs · open for full record →</span>
      </div>
    </button>
  );
}
