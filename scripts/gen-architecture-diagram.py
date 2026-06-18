"""Render docs/architecture.png — the zero-move reference architecture.

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
BOX = "#0d1117"
FILL_EDGE = "#dbeafe"
FILL_INT = "#ffe3e3"
FILL_GW = "#fff4ce"


def box(ax, x, y, w, h, label, fill, edge=BOX):
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.6,
            edgecolor=edge,
            facecolor=fill,
            zorder=3,
        )
    )
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9, zorder=4, wrap=True)


def arrow(ax, x1, y1, x2, y2, label="", color="#444", style="-|>"):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": style, "color": color, "lw": 1.6, "shrinkA": 2, "shrinkB": 2},
        zorder=2,
    )
    if label:
        ax.text(
            (x1 + x2) / 2,
            (y1 + y2) / 2 + 0.12,
            label,
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=color,
            zorder=5,
        )


def main() -> int:
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.2)
    ax.axis("off")

    ax.set_title(
        "NASA API-first, zero-move data marketplace (local OSS analogue)",
        fontsize=13,
        fontweight="bold",
        pad=14,
    )

    # network bands
    ax.add_patch(
        mpatches.Rectangle(
            (0.2, 0.4), 11.6, 3.0, facecolor="#f0f6ff", edgecolor=EDGE, lw=1.2, ls="--", zorder=0
        )
    )
    ax.text(
        0.35,
        3.25,
        "edge network  (clients / catalog / mcp)",
        color=EDGE,
        fontsize=8.5,
        fontweight="bold",
        zorder=1,
    )
    ax.add_patch(
        mpatches.Rectangle(
            (0.2, 4.0),
            11.6,
            2.6,
            facecolor="#fff5f5",
            edgecolor=INTERNAL,
            lw=1.2,
            ls="--",
            zorder=0,
        )
    )
    ax.text(
        0.35,
        6.4,
        "internal network  (no host ports; postgres + dab only)",
        color=INTERNAL,
        fontsize=8.5,
        fontweight="bold",
        zorder=1,
    )

    # edge boxes
    box(ax, 0.5, 1.4, 2.1, 1.1, "Consumers\nPython CLI + MCP agent", FILL_EDGE)
    box(ax, 0.5, 0.6, 2.1, 0.6, "Identity issuer\n(RS256 JWT + JWKS)", FILL_EDGE)
    box(ax, 9.4, 1.4, 2.1, 1.1, "Catalog\nOpenAPI + owner +\nclassification", FILL_EDGE)
    box(ax, 9.4, 0.55, 2.1, 0.6, "Prometheus + Grafana\nper-consumer metrics", FILL_EDGE)

    # gateway (sits in the edge band, just below the internal band)
    box(
        ax,
        4.5,
        1.5,
        3.0,
        2.4,
        "Kong Gateway (OSS, DB-less)\nJWT . rate-limit . meter\ncorrelation-id . OWASP guard\n\nthe ONLY path to data",
        FILL_GW,
        edge=EDGE,
    )

    # internal boxes
    box(ax, 4.5, 4.5, 3.0, 1.0, "Data API Builder\nauto REST + GraphQL + OpenAPI", FILL_INT)
    box(
        ax,
        9.1,
        4.5,
        2.4,
        1.0,
        "PostgreSQL 16\nsynthetic SAP procurement\n(system of record)",
        FILL_INT,
    )

    # arrows
    arrow(ax, 2.6, 2.0, 4.5, 2.4, "bearer token", EDGE)
    arrow(ax, 1.55, 1.2, 1.55, 1.4, "", "#888")
    arrow(ax, 2.6, 0.9, 4.5, 1.9, "JWKS / RS256 key", "#888")
    arrow(ax, 6.0, 3.9, 6.0, 4.5, "REST / OData", INTERNAL, style="<|-|>")
    arrow(ax, 7.5, 5.0, 9.1, 5.0, "SQL (stays put)", INTERNAL, style="<|-|>")
    arrow(ax, 7.5, 2.6, 9.4, 2.2, "publishes contract", "#888")
    arrow(ax, 7.5, 1.9, 9.4, 0.9, "scrape /metrics", "#888")

    fig.text(
        0.5,
        0.02,
        "Data never leaves Postgres - every call is brokered, authenticated, "
        "rate-limited, and metered by the gateway.",
        ha="center",
        fontsize=8.5,
        style="italic",
        color="#555",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
