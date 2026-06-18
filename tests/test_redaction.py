"""Field-level redaction is real, not just claimed.

The `data/classification.yml` manifest marks certain columns **Confidential**
(material unit cost, PO net price/value). Data API Builder enforces this at the
data-API layer via per-role column permissions (`fields.exclude` on the default
`anonymous` role) — so those columns never leave the system of record for a
marketplace consumer, even though the rows themselves are returned.

This is the robust, DAB-native equivalent of column-level masking in Microsoft
Purview / SQL — applied before exposure, not bolted onto the gateway response.
"""

from __future__ import annotations

from conftest import gateway_get, get_token, requires_stack

# Columns classified Confidential in data/classification.yml that must be redacted
# from the default (anonymous, gateway) consumer's responses.
REDACTED = {
    "/api/Material": ["std_unit_cost_usd"],
    "/api/PurchaseOrder": ["netpr", "netwr"],
}


@requires_stack
def test_confidential_fields_are_redacted_through_the_gateway():
    token = get_token("analyst")
    for path, confidential in REDACTED.items():
        resp = gateway_get(f"{path}?$first=3", token=token)
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"
        rows = resp.json()["value"]
        assert rows, f"{path} returned no rows"
        for row in rows:
            for field in confidential:
                assert field not in row, f"{path}: confidential field '{field}' leaked"


@requires_stack
def test_routine_fields_still_present():
    """Redaction is surgical — non-confidential columns are unaffected."""
    token = get_token("analyst")
    row = gateway_get("/api/Material?$first=1", token=token).json()["value"][0]
    for field in ("matnr", "maktx", "program", "criticality", "std_lead_time_days"):
        assert field in row, f"routine field '{field}' unexpectedly missing"


@requires_stack
def test_redaction_holds_against_role_header_injection():
    """A client cannot un-redact by spoofing the DAB role header.

    DAB's StaticWebApps provider would honor X-MS-CLIENT-PRINCIPAL / X-MS-API-ROLE; the
    gateway strips those inbound headers, so a confidential column stays redacted even
    when a caller tries to assert the privileged `authenticated` role.
    """
    token = get_token("analyst")
    spoof = {
        "X-MS-API-ROLE": "authenticated",
        "X-MS-CLIENT-PRINCIPAL": "eyJ1c2VyUm9sZXMiOlsiYXV0aGVudGljYXRlZCJdfQ==",  # {"userRoles":["authenticated"]}
    }
    resp = gateway_get("/api/Material?$first=1", token=token, headers=spoof)
    assert resp.status_code == 200, f"-> {resp.status_code}"
    row = resp.json()["value"][0]
    assert "std_unit_cost_usd" not in row, "confidential column leaked via role-header injection"
