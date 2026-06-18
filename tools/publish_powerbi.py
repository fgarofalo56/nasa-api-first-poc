#!/usr/bin/env python3
"""Publish the Artemis PBIP (semantic model + report) to a Power BI / Fabric workspace.

Uses fabric-cicd with the Azure CLI credential, so just `az login` into the workspace's
tenant first (no service principal needed for a manual publish). The report binds to the
semantic model automatically.

After publishing, the report shows a connection error until you (one-time, in the Service):
  1. Semantic model -> Settings -> Parameters: set DatabricksServerHostname,
     DatabricksHttpPath (the SQL warehouse HTTP path), CatalogName (dbw_btfabric_dev).
  2. Semantic model -> Settings -> Data source credentials: sign in to the Azure
     Databricks source with your Entra ID (DirectQuery — zero copy).
See powerbi/README.md.

Usage:
  pip install fabric-cicd
  az login --use-device-code            # into the workspace tenant (e.g. limitlessdata.ai)
  WORKSPACE_ID=<guid> python tools/publish_powerbi.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from azure.identity import AzureCliCredential
from fabric_cicd import FabricWorkspace, publish_all_items

# Default: the "csa-loom" workspace in the Limitless Data tenant.
WORKSPACE_ID = os.environ.get("WORKSPACE_ID", "46c42501-e97a-4295-8cdb-b1c7000cce1f")
PBIP_DIR = str(Path(__file__).resolve().parent.parent / "powerbi")


def main() -> None:
    ws = FabricWorkspace(
        workspace_id=WORKSPACE_ID,
        repository_directory=PBIP_DIR,
        item_type_in_scope=["SemanticModel", "Report"],
        token_credential=AzureCliCredential(),
    )
    publish_all_items(ws)
    print(f"Published ArtemisSupplyRisk (SemanticModel + Report) to workspace {WORKSPACE_ID}", file=sys.stderr)


if __name__ == "__main__":
    main()
