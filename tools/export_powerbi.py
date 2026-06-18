#!/usr/bin/env python3
"""Export the Artemis report + semantic model from the Power BI Service into powerbi/.

Power BI reports aren't authored headlessly, so the report is built/edited in the Service
(Copilot) and this pulls the working definition back into the repo as code (Fabric REST
getDefinition). It rebinds the report to the local model (byPath) and genericizes the
environment-specific Databricks identifiers, so the committed PBIP stays clean + portable.
Pair with publish_powerbi.py (push) — this is the pull.

Usage:
  pip install azure-identity
  az login --use-device-code                 # the workspace tenant
  WORKSPACE_ID=<guid> REPORT_ID=<guid> MODEL_ID=<guid> python tools/export_powerbi.py
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from pathlib import Path

from azure.identity import AzureCliCredential

WS = os.environ.get("WORKSPACE_ID", "00000000-0000-0000-0000-000000000000")
REPORT_ID = os.environ.get("REPORT_ID", "")
MODEL_ID = os.environ.get("MODEL_ID", "")
BASE = "https://api.fabric.microsoft.com/v1"
OUT = Path(__file__).resolve().parent.parent / "powerbi"
# Strip environment specifics so the committed PBIP carries no real host/warehouse ids.
GENERICIZE = {
    "7405607213468698": "XXXXXXXXXXXXXXXX",
    "973dba4787484119": "REPLACE_WITH_WAREHOUSE_ID",
}

_tok = AzureCliCredential().get_token("https://api.fabric.microsoft.com/.default").token
HDR = {"Authorization": f"Bearer {_tok}", "Content-Type": "application/json"}


def _req(method: str, url: str, data: dict | None = None):
    r = urllib.request.Request(
        url,
        data=(json.dumps(data).encode() if data is not None else None),
        headers=HDR,
        method=method,
    )
    return urllib.request.urlopen(r, timeout=60)


def _get_definition(kind: str, item_id: str, fmt: str) -> list[dict]:
    resp = _req("POST", f"{BASE}/workspaces/{WS}/{kind}/{item_id}/getDefinition?format={fmt}", {})
    if resp.status == 200:
        return json.loads(resp.read())["definition"]["parts"]
    op = resp.headers.get("Location")
    while True:
        time.sleep(int(resp.headers.get("Retry-After", "3")) if resp.headers else 3)
        s = json.loads(_req("GET", op).read())
        if s.get("status") == "Succeeded":
            break
        if s.get("status") == "Failed":
            raise RuntimeError(f"getDefinition failed: {s}")
    return json.loads(_req("GET", op + "/result").read())["definition"]["parts"]


def _write(parts: list[dict], subdir: str) -> None:
    root = OUT / subdir
    for p in parts:
        path = root / p["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (
            base64.b64decode(p["payload"])
            if p.get("payloadType") == "InlineBase64"
            else p["payload"].encode()
        )
        text = raw.decode("utf-8", errors="ignore")
        for a, b in GENERICIZE.items():
            text = text.replace(a, b)
        path.write_text(text, encoding="utf-8")
    print(f"  {subdir}: {len(parts)} parts")


def main() -> None:
    if not (REPORT_ID and MODEL_ID):
        raise SystemExit("set REPORT_ID and MODEL_ID (and WORKSPACE_ID) env vars")
    _write(_get_definition("reports", REPORT_ID, "PBIR"), "ArtemisSupplyRisk.Report")
    _write(_get_definition("semanticModels", MODEL_ID, "TMDL"), "ArtemisSupplyRisk.SemanticModel")
    # Rebind the report to the local model so the PBIP is self-contained.
    (OUT / "ArtemisSupplyRisk.Report" / "definition.pbir").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
                "version": "4.0",
                "datasetReference": {"byPath": {"path": "../ArtemisSupplyRisk.SemanticModel"}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("Exported + genericized into", OUT)


if __name__ == "__main__":
    main()
