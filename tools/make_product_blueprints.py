#!/usr/bin/env python3
"""Generate per-component "blueprint render" SVGs for the marketplace UI.

The marketplace drill-down detail and the agent's detail card show an engineering
visual for each material. Real photos would be licence-encumbered and would not match
*synthetic* part names, so we render a distinctive, on-brand schematic per component
instead — vector, tiny, ITAR-safe (nothing real), and visibly intentional.

Output: frontend/public/img/products/<slug>.svg, one per material name in
data/synthetic_data.py's _FAMILIES. <slug> must match the JS slug() in
frontend/src/labels.js (lowercase, non-alphanumerics -> '-', collapsed, trimmed).

Run:  python tools/make_product_blueprints.py
"""

from __future__ import annotations

import re
from pathlib import Path

# Mirror of data/synthetic_data.py _FAMILIES (kept in sync by tests/UI by name).
FAMILIES: list[tuple[str, tuple[str, ...]]] = [
    ("Avionics", ("Flight computer module", "Inertial measurement unit", "RAD-hard FPGA board")),
    ("Propulsion", ("Turbopump impeller", "Combustion chamber liner", "Cryo valve assembly")),
    ("Structures", ("Composite interstage panel", "Titanium thrust bracket", "Al-Li dome gore")),
    ("Thermal", ("Ablative TPS tile", "MLI blanket set", "Heat-pipe radiator panel")),
    ("Power", ("Li-ion battery module", "Solar array wing", "Power distribution unit")),
    ("EEE", ("Space-grade DC-DC converter", "Rad-hard memory array", "Connector backshell")),
    ("Software", ("Flight software license", "Ground command toolkit", "Telemetry decoder")),
    ("GSE", ("Mobile launcher umbilical", "Cryo transfer line", "Pad water deluge nozzle")),
]

W, H = 480, 320
BG = "#071633"
GRID = "#2b6cb0"
STROKE = "#cfe8ff"
ACCENT = "#fc3d21"
TEXT = "#eaf4ff"
MUTED = "#7fa9d8"


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return s.strip("-")


# ── motif library (centred roughly on 240,138; ~360x190 drawing area) ──
# Each returns the inner SVG markup for one component's schematic.


def m_flight_computer() -> str:
    chips = "".join(
        f'<rect x="{150 + (i % 3) * 70}" y="{70 + (i // 3) * 60}" width="46" height="34" rx="3" '
        f'fill="none" stroke="{STROKE}" stroke-width="2"/>'
        for i in range(6)
    )
    pins = "".join(f'<line x1="{140 + i * 18}" y1="200" x2="{140 + i * 18}" y2="214" stroke="{ACCENT}" stroke-width="2"/>' for i in range(12))
    return (
        f'<rect x="120" y="50" width="240" height="160" rx="6" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'{chips}<circle cx="335" cy="78" r="6" fill="none" stroke="{ACCENT}" stroke-width="2"/>{pins}'
    )


def m_imu() -> str:
    rings = (
        f'<ellipse cx="240" cy="135" rx="80" ry="30" fill="none" stroke="{STROKE}" stroke-width="2"/>'
        f'<ellipse cx="240" cy="135" rx="30" ry="80" fill="none" stroke="{STROKE}" stroke-width="2"/>'
        f'<ellipse cx="240" cy="135" rx="58" ry="58" fill="none" stroke="{ACCENT}" stroke-width="2"/>'
    )
    return f'<rect x="222" y="117" width="36" height="36" fill="none" stroke="{STROKE}" stroke-width="2.5"/>{rings}'


def m_fpga() -> str:
    grid = "".join(
        f'<circle cx="{206 + (i % 6) * 14}" cy="{104 + (i // 6) * 14}" r="3" fill="{STROKE}"/>'
        for i in range(36)
    )
    return (
        f'<rect x="120" y="55" width="240" height="150" rx="5" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<rect x="195" y="95" width="90" height="80" rx="4" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>{grid}'
    )


def m_turbopump() -> str:
    blades = "".join(
        f'<path d="M240 135 q {30 + 0} {-18}, {60} {-6}" fill="none" stroke="{STROKE}" stroke-width="2.5" transform="rotate({a} 240 135)"/>'
        for a in range(0, 360, 36)
    )
    return (
        f'<circle cx="240" cy="135" r="78" fill="none" stroke="{STROKE}" stroke-width="2"/>'
        f'<circle cx="240" cy="135" r="22" fill="none" stroke="{ACCENT}" stroke-width="3"/>{blades}'
        f'<circle cx="240" cy="135" r="6" fill="{ACCENT}"/>'
    )


def m_combustion() -> str:
    return (
        f'<path d="M195 60 L285 60 L300 130 Q240 230 180 130 Z" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<path d="M210 70 L270 70 L283 128 Q240 200 197 128 Z" fill="none" stroke="{GRID}" stroke-width="1.5"/>'
        + "".join(f'<line x1="{200 + i * 16}" y1="62" x2="{200 + i * 16}" y2="120" stroke="{ACCENT}" stroke-width="1.2" opacity="0.7"/>' for i in range(6))
    )


def m_cryo_valve() -> str:
    return (
        f'<rect x="200" y="110" width="80" height="50" rx="4" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<line x1="160" y1="135" x2="200" y2="135" stroke="{STROKE}" stroke-width="6"/>'
        f'<line x1="280" y1="135" x2="320" y2="135" stroke="{STROKE}" stroke-width="6"/>'
        f'<line x1="240" y1="110" x2="240" y2="70" stroke="{STROKE}" stroke-width="3"/>'
        f'<ellipse cx="240" cy="66" rx="34" ry="9" fill="none" stroke="{ACCENT}" stroke-width="3"/>'
        f'<path d="M226 135 L240 122 L254 135 L240 148 Z" fill="none" stroke="{ACCENT}" stroke-width="2"/>'
    )


def m_interstage() -> str:
    stringers = "".join(f'<line x1="{150 + i * 30}" y1="70" x2="{150 + i * 30}" y2="200" stroke="{STROKE}" stroke-width="1.6"/>' for i in range(7))
    return (
        f'<rect x="140" y="70" width="200" height="130" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<ellipse cx="240" cy="70" rx="100" ry="16" fill="none" stroke="{ACCENT}" stroke-width="2"/>'
        f'<ellipse cx="240" cy="200" rx="100" ry="16" fill="none" stroke="{ACCENT}" stroke-width="2"/>{stringers}'
    )


def m_bracket() -> str:
    holes = "".join(f'<circle cx="{cx}" cy="{cy}" r="7" fill="none" stroke="{ACCENT}" stroke-width="2"/>' for cx, cy in [(175, 95), (305, 95), (175, 185)])
    return (
        f'<path d="M160 80 L320 80 L320 110 L195 110 L195 200 L160 200 Z" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<path d="M200 115 L300 115 L205 195 Z" fill="none" stroke="{GRID}" stroke-width="1.5"/>{holes}'
    )


def m_dome_gore() -> str:
    return (
        f'<path d="M240 60 Q330 135 240 210 Q150 135 240 60 Z" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<path d="M240 60 L240 210" stroke="{ACCENT}" stroke-width="1.5"/>'
        + "".join(f'<path d="M{240 - d} {135 - 0} Q240 {72 + i*3} {240 + d} {135}" fill="none" stroke="{GRID}" stroke-width="1.2"/>' for i, d in enumerate([60, 40, 20]))
    )


def m_tps_tile() -> str:
    return (
        f'<polygon points="200,80 280,80 320,135 280,190 200,190 160,135" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<polygon points="210,92 270,92 303,135 270,178 210,178 177,135" fill="none" stroke="{GRID}" stroke-width="1.5"/>'
        f'<polygon points="222,106 258,106 281,135 258,164 222,164 199,135" fill="none" stroke="{ACCENT}" stroke-width="1.6"/>'
    )


def m_mli() -> str:
    return "".join(
        f'<path d="M150 {80 + i * 18} q 45 -12 90 0 t 90 0" fill="none" stroke="{STROKE if i % 2 else GRID}" stroke-width="2"/>'
        for i in range(7)
    ) + f'<line x1="150" y1="80" x2="150" y2="188" stroke="{ACCENT}" stroke-width="2"/><line x1="330" y1="80" x2="330" y2="188" stroke="{ACCENT}" stroke-width="2"/>'


def m_radiator() -> str:
    tubes = "".join(f'<line x1="150" y1="{82 + i * 14}" x2="330" y2="{82 + i * 14}" stroke="{STROKE}" stroke-width="2"/>' for i in range(9))
    return (
        f'<rect x="140" y="72" width="200" height="128" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>{tubes}'
        f'<line x1="140" y1="72" x2="140" y2="200" stroke="{STROKE}" stroke-width="5"/>'
    )


def m_battery() -> str:
    cells = "".join(
        f'<rect x="{160 + (i % 4) * 42}" y="{90 + (i // 4) * 50}" width="30" height="40" rx="14" fill="none" stroke="{STROKE}" stroke-width="2"/>'
        f'<line x1="{175 + (i % 4) * 42}" y1="90" x2="{175 + (i % 4) * 42}" y2="84" stroke="{ACCENT}" stroke-width="3"/>'
        for i in range(8)
    )
    return f'<rect x="146" y="76" width="190" height="120" rx="6" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>{cells}'


def m_solar() -> str:
    cells = "".join(
        f'<rect x="{150 + (i % 6) * 30}" y="{80 + (i // 6) * 36}" width="26" height="32" fill="none" stroke="{STROKE}" stroke-width="1.4"/>'
        for i in range(18)
    )
    return f'<rect x="146" y="76" width="190" height="116" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>{cells}<line x1="146" y1="134" x2="120" y2="134" stroke="{STROKE}" stroke-width="4"/>'


def m_pdu() -> str:
    bars = "".join(f'<rect x="{165 + i * 40}" y="100" width="20" height="70" fill="none" stroke="{STROKE}" stroke-width="2"/>' for i in range(4))
    return (
        f'<rect x="140" y="80" width="200" height="110" rx="5" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>{bars}'
        f'<line x1="150" y1="92" x2="330" y2="92" stroke="{STROKE}" stroke-width="3"/>'
    )


def m_dcdc() -> str:
    coil = "".join(f'<circle cx="{280 + (i % 2) * 0}" cy="{110 + i * 12}" r="9" fill="none" stroke="{STROKE}" stroke-width="2"/>' for i in range(5))
    caps = "".join(f'<rect x="{165 + i * 22}" y="105" width="14" height="34" rx="6" fill="none" stroke="{ACCENT}" stroke-width="2"/>' for i in range(3))
    return f'<rect x="140" y="80" width="200" height="120" rx="5" fill="none" stroke="{STROKE}" stroke-width="2.5"/>{coil}{caps}'


def m_memory() -> str:
    grid = "".join(
        f'<rect x="{180 + (i % 7) * 18}" y="{96 + (i // 7) * 18}" width="12" height="12" fill="none" stroke="{STROKE}" stroke-width="1.2"/>'
        for i in range(35)
    )
    return f'<rect x="160" y="80" width="170" height="120" rx="4" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>{grid}'


def m_backshell() -> str:
    pins = "".join(f'<circle cx="{240 + 34 * __import__("math").cos(a)}" cy="{135 + 34 * __import__("math").sin(a)}" r="4" fill="{STROKE}"/>' for a in [i * 0.5236 for i in range(12)])
    return (
        f'<circle cx="240" cy="135" r="62" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<circle cx="240" cy="135" r="48" fill="none" stroke="{ACCENT}" stroke-width="2"/>{pins}'
        f'<circle cx="240" cy="135" r="6" fill="{ACCENT}"/>'
        f'<rect x="296" y="120" width="44" height="30" rx="8" fill="none" stroke="{STROKE}" stroke-width="2"/>'
    )


def m_fsw_license() -> str:
    return (
        f'<rect x="170" y="70" width="140" height="170" rx="6" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        + "".join(f'<line x1="190" y1="{100 + i * 20}" x2="290" y2="{100 + i * 20}" stroke="{GRID}" stroke-width="2"/>' for i in range(5))
        + f'<text x="240" y="160" font-family="monospace" font-size="34" fill="{ACCENT}" text-anchor="middle">{{ }}</text>'
        + f'<circle cx="290" cy="225" r="16" fill="none" stroke="{ACCENT}" stroke-width="2"/>'
    )


def m_ground_toolkit() -> str:
    return (
        f'<rect x="135" y="75" width="210" height="135" rx="6" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<line x1="135" y1="98" x2="345" y2="98" stroke="{STROKE}" stroke-width="2"/>'
        f'<circle cx="148" cy="87" r="3" fill="{ACCENT}"/><circle cx="160" cy="87" r="3" fill="{STROKE}"/>'
        f'<text x="150" y="135" font-family="monospace" font-size="20" fill="{ACCENT}">&gt;_</text>'
        + "".join(f'<line x1="180" y1="{130 + i * 18}" x2="{300 - i * 20}" y2="{130 + i * 18}" stroke="{GRID}" stroke-width="2"/>' for i in range(4))
    )


def m_telemetry() -> str:
    pts = " ".join(f"{150 + i * 12},{135 + (28 if i % 4 in (1, 2) else -22) * ((-1) ** (i // 2))}" for i in range(16))
    return (
        f'<polyline points="{pts}" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>'
        f'<line x1="140" y1="135" x2="345" y2="135" stroke="{GRID}" stroke-width="1.5"/>'
        f'<rect x="135" y="80" width="46" height="110" fill="none" stroke="{STROKE}" stroke-width="2"/>'
        f'<rect x="300" y="80" width="46" height="110" fill="none" stroke="{STROKE}" stroke-width="2"/>'
    )


def m_umbilical() -> str:
    return (
        f'<line x1="170" y1="60" x2="170" y2="230" stroke="{STROKE}" stroke-width="5"/>'
        f'<rect x="155" y="60" width="30" height="170" fill="none" stroke="{GRID}" stroke-width="1.5"/>'
        f'<line x1="170" y1="100" x2="300" y2="100" stroke="{STROKE}" stroke-width="3"/>'
        f'<rect x="300" y="86" width="40" height="30" rx="4" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>'
        + "".join(f'<path d="M185 {100 + i*2} Q260 {120 + i*8} 300 {104}" fill="none" stroke="{ACCENT}" stroke-width="1.4" opacity="0.7"/>' for i in range(3))
    )


def m_cryo_line() -> str:
    bellows = "".join(f'<line x1="{205 + i * 12}" y1="115" x2="{205 + i * 12}" y2="155" stroke="{STROKE}" stroke-width="2"/>' for i in range(6))
    return (
        f'<rect x="140" y="118" width="60" height="34" rx="6" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<rect x="280" y="118" width="60" height="34" rx="6" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<rect x="200" y="112" width="80" height="46" fill="none" stroke="{ACCENT}" stroke-width="2"/>{bellows}'
        f'<text x="240" y="100" font-family="monospace" font-size="14" fill="{MUTED}" text-anchor="middle">LN2</text>'
    )


def m_deluge() -> str:
    arcs = "".join(f'<path d="M240 150 Q{200 + i * 20} {210}, {160 + i * 30} 250" fill="none" stroke="{STROKE}" stroke-width="1.6" opacity="0.8"/>' for i in range(5))
    return (
        f'<rect x="225" y="70" width="30" height="60" fill="none" stroke="{STROKE}" stroke-width="2.5"/>'
        f'<path d="M215 130 L265 130 L245 150 L235 150 Z" fill="none" stroke="{ACCENT}" stroke-width="2.5"/>{arcs}'
        f'<line x1="240" y1="60" x2="240" y2="70" stroke="{STROKE}" stroke-width="6"/>'
    )


MOTIFS = {
    "Flight computer module": m_flight_computer,
    "Inertial measurement unit": m_imu,
    "RAD-hard FPGA board": m_fpga,
    "Turbopump impeller": m_turbopump,
    "Combustion chamber liner": m_combustion,
    "Cryo valve assembly": m_cryo_valve,
    "Composite interstage panel": m_interstage,
    "Titanium thrust bracket": m_bracket,
    "Al-Li dome gore": m_dome_gore,
    "Ablative TPS tile": m_tps_tile,
    "MLI blanket set": m_mli,
    "Heat-pipe radiator panel": m_radiator,
    "Li-ion battery module": m_battery,
    "Solar array wing": m_solar,
    "Power distribution unit": m_pdu,
    "Space-grade DC-DC converter": m_dcdc,
    "Rad-hard memory array": m_memory,
    "Connector backshell": m_backshell,
    "Flight software license": m_fsw_license,
    "Ground command toolkit": m_ground_toolkit,
    "Telemetry decoder": m_telemetry,
    "Mobile launcher umbilical": m_umbilical,
    "Cryo transfer line": m_cryo_line,
    "Pad water deluge nozzle": m_deluge,
}


def frame(name: str, family: str, motif: str) -> str:
    vlines = "".join(f'<line x1="{i * 20}" y1="0" x2="{i * 20}" y2="{H}" />' for i in range(W // 20 + 1))
    hlines = "".join(f'<line x1="0" y1="{i * 20}" x2="{W}" y2="{i * 20}" />' for i in range(H // 20 + 1))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Blueprint schematic of {name} ({family}) — synthetic">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <g stroke="{GRID}" stroke-width="0.5" opacity="0.28">{vlines}{hlines}</g>
  <rect x="8" y="8" width="{W - 16}" height="{H - 16}" fill="none" stroke="{STROKE}" stroke-width="1" opacity="0.5"/>
  <g>{motif}</g>
  <text x="20" y="40" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="700" fill="{TEXT}">{name}</text>
  <text x="20" y="{H - 22}" font-family="monospace" font-size="12" fill="{MUTED}">FAMILY: {family.upper()}  ·  REV —  ·  NTS</text>
  <text x="{W - 20}" y="{H - 22}" font-family="monospace" font-size="11" fill="{ACCENT}" text-anchor="end" opacity="0.85">SYNTHETIC · NOT REAL NASA DATA</text>
  <path d="M{W - 60} 20 h40 v40" fill="none" stroke="{ACCENT}" stroke-width="1.5" opacity="0.7"/>
</svg>
"""


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "frontend" / "public" / "img" / "products"
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for family, parts in FAMILIES:
        for name in parts:
            motif_fn = MOTIFS.get(name)
            if motif_fn is None:
                raise SystemExit(f"No motif for {name!r}")
            svg = frame(name, family, motif_fn())
            path = out / f"{slug(name)}.svg"
            path.write_text(svg, encoding="utf-8")
            written.append(path.name)
    print(f"Wrote {len(written)} blueprints to {out}")
    for n in sorted(written):
        print(f"  {n}")


if __name__ == "__main__":
    main()
