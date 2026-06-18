"""The headline supply-risk query — deterministic data + governed gateway answer.

Two layers:
  * `test_generator_*` always run (no stack): prove the seeded generator is
    reproducible and the known high-risk Artemis-3 row exists.
  * `test_gateway_*` run only with the stack up: prove the same answer comes back
    *through Kong* against the DAB `SupplyRisk` entity.
"""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

import pytest
from conftest import REPO_ROOT, gateway_get, get_token, requires_stack

sys.path.insert(0, str(REPO_ROOT))

from data.synthetic_data import generate_artemis_procurement  # noqa: E402

# The deterministic (seed=42) headline row: the single Artemis-3 Critical, sole-source
# material whose average delay exceeds 30 days.
EXPECTED_TOP_MATNR = "NSN-7209-452737"
EXPECTED_TOP_NAME = "Mobile launcher umbilical"


@pytest.fixture(scope="module")
def risk_rows() -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        generate_artemis_procurement(tmp, seed=42)
        with open(Path(tmp) / "artemis_supply_risk.csv", encoding="utf-8") as f:
            return list(csv.DictReader(f))


def test_generator_counts_are_reproducible():
    with tempfile.TemporaryDirectory() as tmp:
        result = generate_artemis_procurement(tmp, seed=42)
    counts = result["counts"]
    assert counts["vendors"] == 26
    assert counts["materials"] == 60
    assert counts["purchase_orders"] == 240
    assert counts["supply_risk"] == 59
    assert counts["high_risk_materials"] == 11
    assert counts["sole_source_materials"] == 14


def _headline(rows: list[dict]) -> list[dict]:
    """Critical, sole-source Artemis-3 materials slipping > 30 days, by risk desc."""
    hits = [
        r
        for r in rows
        if r["PROGRAM"] == "Artemis-3"
        and r["CRITICALITY"] == "Critical"
        and r["SOLE_SOURCE"] == "X"
        and float(r["AVG_DELAY_DAYS"]) > 30
    ]
    return sorted(hits, key=lambda r: int(r["RISK_SCORE"]), reverse=True)


def test_generator_headline_row_present(risk_rows):
    hits = _headline(risk_rows)
    assert hits, "expected at least one Artemis-3 high-risk row from seed=42"
    top = hits[0]
    assert top["MATNR"] == EXPECTED_TOP_MATNR
    assert top["MAKTX"] == EXPECTED_TOP_NAME
    assert top["RISK_TIER"] == "High"
    assert int(top["RISK_SCORE"]) >= 70


# ── governed path: the same answer through Kong → DAB ──────────────────────────────


@requires_stack
@pytest.mark.integration
def test_gateway_supply_risk_returns_headline_row():
    token = get_token("analyst")
    flt = (
        "$filter=program eq 'Artemis-3' and criticality eq 'Critical' "
        "and sole_source eq true and avg_delay_days gt 30"
        "&$orderby=risk_score desc"
    )
    resp = gateway_get(f"/api/SupplyRisk?{flt}", token=token)
    assert resp.status_code == 200, resp.text
    rows = resp.json()["value"]
    matnrs = {r["matnr"] for r in rows}
    assert EXPECTED_TOP_MATNR in matnrs, f"expected {EXPECTED_TOP_MATNR} in {matnrs}"
