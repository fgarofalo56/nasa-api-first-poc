"""Hard constraint (PRP §9): no Microsoft Fabric / OneLake as a component anywhere.

Fabric/OneLake are not available in Azure Government / GCC, so they must not appear as
a *component* or *recommendation*. A single "explicitly excluded, and why" mention in
docs is allowed — those mentions must sit next to an exclusion marker
("excluded" / "not available" / "not in Azure Gov" / "intentionally" / ...).

We match only the *product* terms ("microsoft fabric", "onelake") so the ordinary
English word "fabric" ("fabricated data", "integration fabric") is not a false hit.
The constraint-defining meta files (PRP.md, CLAUDE.md, this test) are not scanned —
they specify the rule rather than build a component.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_SCAN_SUFFIXES = {".py", ".md", ".json", ".yml", ".yaml", ".bicep", ".sh", ".toml"}
_SKIP_DIRS = {
    ".git",
    ".github",
    "node_modules",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    "temp",
}
# Meta files that *specify* the constraint rather than implement a component.
_SKIP_FILES = {"PRP.md", "CLAUDE.md", "test_no_fabric.py"}

_PRODUCT_TERMS = re.compile(r"microsoft fabric|onelake", re.IGNORECASE)
_EXCLUSION_MARKERS = (
    "exclud",
    "not available",
    "not in azure gov",
    "not in gov",
    "do not introduce",
    "intentionally",
    "remain",
    "no microsoft fabric",
    "prohibit",
)
_WINDOW = 220  # chars of context around a match to look for an exclusion marker


def _iter_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in _SCAN_SUFFIXES:
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if "data/out" in path.relative_to(REPO_ROOT).as_posix():
            continue
        if path.name in _SKIP_FILES:
            continue
        yield path


def test_no_fabric_or_onelake_as_component():
    offenders: list[str] = []
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        low = text.lower()
        for m in _PRODUCT_TERMS.finditer(text):
            start = max(0, m.start() - _WINDOW)
            window = low[start : m.end() + _WINDOW]
            if any(marker in window for marker in _EXCLUSION_MARKERS):
                continue  # allowed: explicit "excluded, and why" mention
            lineno = text.count("\n", 0, m.start()) + 1
            rel = path.relative_to(REPO_ROOT).as_posix()
            offenders.append(f"{rel}:{lineno}: {m.group(0)}")
    assert not offenders, (
        "Fabric/OneLake referenced as a component (no nearby exclusion marker):\n"
        + "\n".join(offenders)
    )
