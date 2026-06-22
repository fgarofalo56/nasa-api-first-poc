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
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fontsize, zorder=4)


def arrow(ax, x1, y1, x2, y2, label="", color="#444", style="-|>", lx=None, ly=None):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops={"arrowstyle": style, "color": color, "lw": 1.6, "shrinkA": 2, "shrinkB": 2},
        zorder=2,
    )
    if label:
        ax.text(
            lx if lx is not None else (x1 + x2) / 2,
            ly if ly is not None else (y1 + y2) / 2 + 0.12,
            label,
            ha="center",
            va="center",
            fontsize=7.3,
            color=color,
            zorder=6,
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.9,
            },
        )


def main() -> int:
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.axis("off")
    ax.set_title(
        "NASA API-first, zero-move, multi-source data marketplace (local OSS analogue)",
        fontsize=13,
        fontweight="bold",
        pad=14,
    )

    # --- network bands (edge below, internal above; Kong is the only bridge) ---
    ax.add_patch(
        mpatches.Rectangle(
            (0.2, 0.35), 12.6, 3.55, facecolor="#f0f6ff", edgecolor=EDGE, lw=1.2, ls="--", zorder=0
        )
    )
    ax.text(
        0.45,
        3.62,
        "edge network  ·  host-exposed  (consumers · UI · catalog · metrics · registry)",
        color=EDGE,
        fontsize=8.5,
        fontweight="bold",
        zorder=1,
    )
    ax.add_patch(
        mpatches.Rectangle(
            (0.2, 4.35),
            12.6,
            2.95,
            facecolor="#fff5f5",
            edgecolor=INTERNAL,
            lw=1.2,
            ls="--",
            zorder=0,
        )
    )
    ax.text(
        0.45,
        7.02,
        "internal network  ·  no host ports  (sources reachable only via Kong)",
        color=INTERNAL,
        fontsize=8.5,
        fontweight="bold",
        zorder=1,
    )

    # --- internal sources: one aligned row (DOT | DAB above Kong | Postgres) ---
    SRC_Y, SRC_H = 4.95, 1.15
    box(
        ax,
        0.7,
        SRC_Y,
        2.7,
        SRC_H,
        "DOT Transportation API\n2nd source · added via wizard",
        FILL_INT,
        fontsize=8.3,
    )
    box(
        ax,
        5.15,
        SRC_Y,
        2.7,
        SRC_H,
        "Data API Builder\nauto REST · GraphQL · OpenAPI",
        FILL_INT,
        fontsize=8.3,
    )
    box(
        ax,
        9.0,
        SRC_Y,
        3.0,
        SRC_H,
        "PostgreSQL 16\nArtemis SAP procurement\n(system of record)",
        FILL_INT,
        fontsize=8.3,
    )

    # --- edge boxes: left (consumers/identity) · center (Kong + registry) · right (catalog/metrics) ---
    box(
        ax,
        0.7,
        2.0,
        2.7,
        1.1,
        "Consumers\nPython CLI · MCP agent\nNASA-themed UI",
        FILL_EDGE,
        fontsize=8.5,
    )
    box(ax, 0.7, 0.5, 2.7, 1.0, "Identity issuer\nRS256 JWT + JWKS", FILL_EDGE, fontsize=8.5)
    box(
        ax,
        9.0,
        2.0,
        3.0,
        1.1,
        "Catalog\nproducts · owner · classification",
        FILL_EDGE,
        fontsize=8.3,
    )
    box(
        ax,
        9.0,
        0.5,
        3.0,
        1.0,
        "Prometheus + Grafana\nper-consumer metrics",
        FILL_EDGE,
        fontsize=8.3,
    )

    box(
        ax,
        5.15,
        1.85,
        2.7,
        1.25,
        "Kong Gateway (OSS)\nJWT · rate-limit · meter\ncorrelation-id · OWASP\nthe ONLY path to data",
        FILL_GW,
        edge=EDGE,
        fontsize=8.5,
    )
    box(
        ax,
        4.6,
        0.5,
        3.8,
        0.95,
        "Registry / control-plane  ·  onboarding wizard",
        FILL_CTL,
        edge=CONTROL,
        fontsize=8.3,
    )

    # --- arrows ---
    # consumers -> kong (governed call)
    arrow(ax, 3.4, 2.55, 5.15, 2.55, "bearer token", EDGE)
    # identity -> kong (key material)
    arrow(ax, 3.4, 1.2, 5.15, 2.1, "JWKS · RS256 key", "#888", lx=4.05, ly=1.78)
    # registry -> kong admin (hot reload)
    arrow(ax, 6.5, 1.45, 6.5, 1.85, "hot-reload /config", CONTROL, lx=6.5, ly=1.65)
    # kong <-> DAB <-> postgres (the zero-move data path)
    arrow(ax, 6.5, 3.1, 6.5, 4.95, "REST / OData", INTERNAL, style="<|-|>", lx=6.5, ly=4.02)
    arrow(ax, 7.85, 5.525, 9.0, 5.525, "SQL (stays put)", INTERNAL, style="<|-|>")
    # kong <-> DOT (federated 2nd source)
    arrow(ax, 5.15, 2.9, 3.4, 4.95, "federated route", INTERNAL, style="<|-|>", lx=3.7, ly=3.95)
    # kong -> catalog / metrics (publishes contract, exposes /metrics)
    arrow(ax, 7.85, 2.7, 9.0, 2.7, "publishes contract", "#888")
    arrow(ax, 7.85, 2.2, 9.0, 1.3, "scrape /metrics", "#888", lx=8.6, ly=1.95)

    fig.text(
        0.5,
        0.025,
        "Data never leaves its source — every call (Artemis or DOT) is brokered, "
        "authenticated, rate-limited, and metered by the gateway. New sources are added "
        "via a live config reload, no restart.",
        ha="center",
        fontsize=8.3,
        style="italic",
        color="#555",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
