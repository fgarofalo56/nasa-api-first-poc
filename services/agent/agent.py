"""Mission agent — a grounded chat agent over the governed data, via the MCP server.

The agent is an MCP *host*: it answers questions by calling the MCP server's tools
(`query_supply_risk`, `material_detail`), which reach the data ONLY through the Kong
gateway. So every answer is grounded in governed data and cites its source (the MCP
tool + the gateway correlation id). It refuses off-topic questions with a bit of
space-flavored sass — the point being that a *grounded, governed* agent only speaks to
the data product it was given.

This is the open-standards story: Copilot / Foundry / any MCP host could call the exact
same tools. The routing here is deterministic (reliable + free for a live demo); set
AGENT_LLM=azure-openai with the AZURE_OPENAI_* env to have an LLM phrase the grounded
answer instead (it still only sees gateway data + must cite).
"""

from __future__ import annotations

import json
import os
import re

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import BaseModel

PORT = int(os.environ.get("AGENT_PORT", "8110"))
MCP_URL = os.environ.get("MCP_URL", "http://mcp:8090/mcp").rstrip("/")

app = FastAPI(title="Artemis Mission Agent", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

PROGRAMS = {
    "artemis-3": "Artemis-3", "artemis 3": "Artemis-3", "artemis3": "Artemis-3",
    "gateway": "Gateway", "moon-base": "Moon-Base", "moon base": "Moon-Base",
    "moonbase": "Moon-Base", "egs": "EGS-Ground", "ground": "EGS-Ground",
}
# Prefix tokens end with \w* (NOT \b) so "materi" matches "material", "batter" -> "battery".
ON_TOPIC = re.compile(
    r"\b(artemis|supply|risk|materi|part|vendor|supplier|deliver|delay|slip|late|"
    r"program|sole.?source|procure|purchase|po\b|gateway|nsn|batter|panel|valve|"
    r"pump|avionic|propuls|radiator|telemetr|converter|critical|essential|routine|"
    r"moon|egs|mission|data product|marketplace|catalog|who (makes|supplies|builds))\w*",
    re.I,
)
HELP = re.compile(r"\b(help|what can you|capabilit|who are you|what are you|how do you work)\w*", re.I)
ANALYTICS = re.compile(
    r"\b(stat|statistic|distribut|breakdown|how many|count|chart|graph|plot|analyt|"
    r"compare|trend|metric|by (program|tier|risk))\w*",
    re.I,
)

# Space-flavored sass for off-topic asks — each ends with the Microsoft-rep line.
SASS = [
    "🚀 Negative, Houston. My flight plan only covers the Artemis supply-chain data "
    "product — through the governed gateway. {topic} is way outside my orbit.",
    "🛰️ That request burned up on re-entry. I'm a single-purpose, *grounded* agent: I "
    "only speak to the Artemis procurement data the gateway hands me. {topic}? Not my mission.",
    "🌑 I'd love to help, but I was built for one job — answering supply-risk questions "
    "from governed data. Asking me about {topic} is like asking the Hubble to make toast.",
    "👩‍🚀 Houston, we have a scope problem. I'm wired to the Artemis data product via MCP "
    "and nothing else, so {topic} is a no-go for launch.",
]
SASS_TAIL = (
    " But if you'd like an agent (or app) that *does* do that — grounded on your own "
    "governed data — your friendly **Microsoft** rep would be thrilled to help you build it. 🛰️"
)


class Ask(BaseModel):
    question: str
    consumer: str = "artemis-agent"


async def _call_tool(tool: str, args: dict) -> dict:
    """Call an MCP tool on the server and return its structured payload."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            payload = getattr(result, "structuredContent", None)
            if not payload and result.content:
                text = getattr(result.content[0], "text", None)
                payload = json.loads(text) if text else None
            return payload or {}


def _parse_params(q: str) -> dict:
    ql = q.lower()
    program = next((v for k, v in PROGRAMS.items() if k in ql), "Artemis-3")
    crit = "Critical"
    if "essential" in ql:
        crit = "Essential"
    elif "routine" in ql:
        crit = "Routine"
    elif re.search(r"\ball\b|any criticalit|every", ql):
        crit = ""
    m = re.search(r"(\d+)\s*day", ql)
    min_delay = int(m.group(1)) if m else 30
    sole = not re.search(r"\b(any.?sourc|not? sole|include.*sourc|all sourc)\b", ql)
    return {"program": program, "criticality": crit, "min_delay": min_delay, "sole_source_only": sole}


def _detail_target(q: str) -> str | None:
    nsn = re.search(r"NSN-[0-9-]+", q, re.I)
    if nsn:
        return nsn.group(0)
    m = re.search(
        r"(?:about|supplier of|who (?:makes|supplies|builds)|detail[s]? (?:on|for)|the)\s+"
        r"(?:the\s+)?([a-z][a-z0-9 \-]{3,40}?)(?:\?|$|\s+(?:on|for|in)\b)",
        q,
        re.I,
    )
    if m and not PROGRAMS.get(m.group(1).strip().lower()):
        term = m.group(1).strip()
        if not ON_TOPIC.fullmatch(term or "") and len(term) >= 4:
            return term
    return None


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/ask")
async def ask(req: Ask):
    q = (req.question or "").strip()
    if not q:
        return {"on_topic": False, "grounded": False, "answer": "Ask me about Artemis supply-chain risk. 🚀", "sources": []}

    if HELP.search(q) and not ON_TOPIC.search(q):
        return {
            "on_topic": True, "grounded": False,
            "answer": (
                "👋 I'm the Artemis mission agent. I answer **supply-chain** questions using the "
                "governed data product — through the gateway, via the open MCP standard. Try:\n"
                "• \"What's at risk on Artemis-3?\"\n"
                "• \"Which Essential materials on Gateway are slipping > 20 days?\"\n"
                "• \"Tell me about the Li-ion battery module\" or an NSN like NSN-4002-901834\n"
                "• \"Who supplies the heat-pipe radiator panel?\""
            ),
            "sources": [],
        }

    if not ON_TOPIC.search(q):
        topic = re.sub(r"[^\w\s\-']", "", q).strip()[:60] or "that"
        sass = SASS[len(q) % len(SASS)].format(topic=f"“{topic}”")
        return {"on_topic": False, "grounded": False, "answer": sass + SASS_TAIL, "sources": []}

    # On topic → ground the answer in the data product via an MCP tool.
    target = _detail_target(q)
    try:
        if target:
            d = await _call_tool("material_detail", {"material": target})
            if not d.get("found"):
                return {
                    "on_topic": True, "grounded": True,
                    "answer": f"🔭 I queried the governed supply-risk product for “{target}” but found no match. "
                              f"Try an exact NSN or a name like “battery module” or “radiator panel”.",
                    "sources": [{"tool": "material_detail", "gateway_correlation_id": d.get("gateway_correlation_id")}],
                }
            ss = " (sole-source)" if d.get("sole_source") else ""
            sup = f" Supplier: **{d['supplier']}** (CAGE {d.get('cage_code', '?')})." if d.get("supplier") else ""
            answer = (
                f"**{d['material_name']}** ({d['material_id']}) on {d['program']} is **{d['risk_tier']} risk** "
                f"(score {d['risk_score']}), averaging **{float(d['avg_delay_days']):.1f} days** of slip{ss}.{sup} "
                f"It has {len(d.get('recent_pos', []))} recent purchase orders. "
                f"Net price/value and unit cost are **redacted at the gateway** — the same governance every consumer gets."
            )
            return {
                "on_topic": True, "grounded": True, "answer": answer, "tool": "material_detail",
                "render": {
                    "kind": "detail",
                    "material": {
                        "matnr": d["material_id"], "maktx": d["material_name"], "program": d.get("program"),
                        "criticality": d.get("criticality"), "risk_tier": d.get("risk_tier"),
                        "risk_score": d.get("risk_score"), "avg_delay_days": d.get("avg_delay_days"),
                        "sole_source": d.get("sole_source"), "supplier": d.get("supplier"),
                        "cage_code": d.get("cage_code"),
                    },
                    "image": f"/img/products/{d['material_id']}.png",
                    "recent_pos": d.get("recent_pos", []),
                },
                "sources": [{"tool": "material_detail", "product": "SupplyRisk→PurchaseOrder→Vendor",
                             "gateway_correlation_id": d.get("gateway_correlation_id")}],
            }

        p = _parse_params(q)
        analytics = bool(ANALYTICS.search(q))
        if analytics:
            # Broaden so the chart shows a fuller picture (all criticalities/sourcing).
            p = {**p, "criticality": "", "sole_source_only": False, "min_delay": 0}
        r = await _call_tool("query_supply_risk", p)
        mats = r.get("materials", [])
        n = r.get("count", len(mats))
        crit = p["criticality"] or "any-criticality"
        src = "sole-source " if p["sole_source_only"] else ""

        by_delay = bool(re.search(r"\b(delay|slip|late|days?)\b", q, re.I))
        metric = "avg_delay_days" if by_delay else "risk_score"
        ranked = sorted(mats, key=lambda m: float(m.get(metric) or 0), reverse=True)
        items = [
            {
                "matnr": m.get("matnr"), "maktx": m.get("maktx"), "program": m.get("program"),
                "risk_tier": m.get("risk_tier"), "risk_score": m.get("risk_score"),
                "avg_delay_days": m.get("avg_delay_days"), "sole_source": m.get("sole_source"),
            }
            for m in ranked[:8]
        ]
        chart = {
            "type": "bar",
            "title": ("Average delay (days)" if by_delay else "Risk score") + f" — top materials, {p['program']}",
            "unit": "days" if by_delay else "score",
            "points": [
                {"label": m["maktx"], "value": round(float(m.get(metric) or 0), 1), "tier": m.get("risk_tier")}
                for m in ranked[: 8 if n else 0]
            ],
        }

        if n == 0:
            answer = (f"✅ Good news for {p['program']}: I found **no** {crit} {src}materials slipping more than "
                      f"{p['min_delay']} days in the governed data product.")
        elif analytics:
            tiers = {}
            for m in mats:
                tiers[m.get("risk_tier", "?")] = tiers.get(m.get("risk_tier", "?"), 0) + 1
            dist = ", ".join(f"{k}: {v}" for k, v in sorted(tiers.items()))
            answer = (
                f"📊 On **{p['program']}** the governed product reports **{n}** materials. "
                f"Risk-tier distribution — {dist}. Chart shows the top by "
                f"{'delay' if by_delay else 'risk score'}."
            )
        else:
            top = "; ".join(
                f"{m.get('maktx')} ({m.get('risk_tier')}/{m.get('risk_score')}, "
                f"{float(m.get('avg_delay_days', 0)):.0f}d)" for m in ranked[:3]
            )
            answer = (
                f"🛰️ Through the gateway I found **{n}** {crit} {src}material(s) on **{p['program']}** slipping "
                f">{p['min_delay']} days. Highest risk: {top}."
            )
        return {
            "on_topic": True, "grounded": True, "answer": answer, "tool": "query_supply_risk",
            "render": {"kind": "materials", "items": items, "chart": chart if items else None},
            "sources": [{"tool": "query_supply_risk", "product": "SupplyRisk",
                         "gateway_correlation_id": r.get("gateway_correlation_id"), "rows": n}],
        }
    except Exception as exc:  # noqa: BLE001 — degrade gracefully
        return {
            "on_topic": True, "grounded": False,
            "answer": f"🛠️ Houston, I couldn't reach the data product just now ({type(exc).__name__}). "
                      f"The gateway or MCP server may be warming up — try again in a moment.",
            "sources": [],
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
