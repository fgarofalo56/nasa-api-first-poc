"""Render docs/architecture.png — the zero-move, multi-source reference architecture.

Pure matplotlib (no external services). Run: python scripts/gen-architecture-diagram.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "docs" / "architecture.png"

EDGE = "#1f6feb"
INTERNAL = "#cf222e"
CONTROL = "#8957e5"
BOX = "#0d1117"
FILL_EDGE = "#dbeafe"
FILL_INT = "#ffe3e3"
FILL_GW = "#fff4ce"
FILL_CTL = "#efe3ff"


def box(ax, x, y, w, h, label, fill, edge=BOX, fontsize=9):
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.6, edgecolor=edge, facecolor=fill, zorder=3,
        )
    )
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fontsize, zorder=4)


def arrow(ax, x1, y1, x2, y2, label="", color="#444", style="-|>"):
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops={"arrowstyle": style, "color": color, "lw": 1.6, "shrinkA": 2, "shrinkB": 2},
        zorder=2,
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label, ha="center", va="bottom",
                fontsize=7.3, color=color, zorder=5)


def main() -> int:
    fig, ax = plt.subplots(figsize=(13, 7.6))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title(
        "NASA API-first, zero-move, multi-source data marketplace (local OSS analogue)",
        fontsize=13, fontweight="bold", pad=12,
    )

    # bands
    ax.add_patch(mpatches.Rectangle((0.2, 0.4), 12.6, 3.1, facecolor="#f0f6ff",
                                    edgecolor=EDGE, lw=1.2, ls="--", zorder=0))
    ax.text(0.35, 3.34, "edge network  (consumers / UI / catalog / registry)", color=EDGE,
            fontsize=8.5, fontweight="bold", zorder=1)
    ax.add_patch(mpatches.Rectangle((0.2, 4.2), 12.6, 3.0, facecolor="#fff5f5",
                                    edgecolor=INTERNAL, lw=1.2, ls="--", zorder=0))
    ax.text(0.35, 7.05, "internal network  (no host ports; sources reachable only via Kong)",
            color=INTERNAL, fontsize=8.5, fontweight="bold", zorder=1)

    # edge boxes
    box(ax, 0.5, 1.5, 2.2, 1.2, "Consumers\nPython CLI · MCP agent\nNASA-themed UI", FILL_EDGE)
    box(ax, 0.5, 0.6, 2.2, 0.7, "Identity issuer\nRS256 JWT + JWKS", FILL_EDGE, fontsize=8.5)
    box(ax, 10.1, 1.55, 2.4, 1.1, "Catalog\nproducts · owner ·\nclassification", FILL_EDGE)
    box(ax, 10.1, 0.55, 2.4, 0.7, "Prometheus + Grafana\nper-consumer metrics", FILL_EDGE, fontsize=8.3)

    # control-plane (registry) — adds sources to the gateway at runtime
    box(ax, 3.15, 0.55, 2.5, 0.8, "Registry / control-plane\n(onboarding wizard)", FILL_CTL, edge=CONTROL, fontsize=8.3)

    # gateway
    box(ax, 5.2, 1.35, 2.6, 2.6,
        "Kong Gateway (OSS)\nJWT · rate-limit · meter\ncorrelation-id · OWASP\n\nthe ONLY path to data",
        FILL_GW, edge=EDGE)

    # internal sources
    box(ax, 5.2, 4.45, 2.6, 1.0, "Data API Builder\nauto REST+GraphQL+OpenAPI", FILL_INT, fontsize=8.6)
    box(ax, 8.9, 4.45, 2.5, 1.0, "PostgreSQL 16\nArtemis SAP procurement\n(system of record)", FILL_INT, fontsize=8.3)
    box(ax, 1.1, 4.45, 2.6, 1.0, "DOT Transportation API\n(2nd source, added via wizard)", FILL_INT, fontsize=8.3)

    # arrows: consumers -> kong
    arrow(ax, 2.7, 2.1, 5.2, 2.4, "bearer token", EDGE)
    arrow(ax, 1.6, 1.3, 1.6, 1.5, "", "#888")
    arrow(ax, 2.7, 0.95, 5.2, 1.9, "JWKS / RS256 key", "#888")
    # kong <-> DAB <-> postgres
    arrow(ax, 6.5, 3.95, 6.5, 4.45, "REST / OData", INTERNAL, style="<|-|>")
    arrow(ax, 7.8, 4.95, 8.9, 4.95, "SQL (stays put)", INTERNAL, style="<|-|>")
    # kong <-> DOT source (federated)
    arrow(ax, 5.2, 3.0, 3.7, 4.45, "federated route", INTERNAL, style="<|-|>")
    # registry -> kong admin (hot reload)
    arrow(ax, 5.65, 1.35, 6.0, 1.35, "", CONTROL)
    arrow(ax, 4.4, 1.35, 5.6, 1.6, "hot-reload /config", CONTROL)
    # kong -> catalog / metrics
    arrow(ax, 7.8, 2.4, 10.1, 2.1, "publishes contract", "#888")
    arrow(ax, 7.8, 1.7, 10.1, 0.95, "scrape /metrics", "#888")

    fig.text(0.5, 0.02,
             "Data never leaves its source — every call (Artemis or DOT) is brokered, "
             "authenticated, rate-limited, and metered by the gateway. New sources are added "
             "via a live config reload, no restart.",
             ha="center", fontsize=8.3, style="italic", color="#555")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
