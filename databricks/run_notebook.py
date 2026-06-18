"""Import + run the zero-move medallion notebook on a Databricks workspace.

Authenticates with the Azure CLI (no PAT needed): `az login` into the tenant, then run.
Creates a secret scope for the source credential, imports the notebook, submits a one-off
job on a single-node Unity-Catalog cluster, waits, and prints the result + a validation
query. Idempotent enough to re-run.

Usage:
  az login
  export PG_ADMIN_PASSWORD='<the deployed Postgres password>'   # for source_mode=postgres
  python databricks/run_notebook.py \
      --host adb-7405607213468698.18.azuredatabricks.net \
      --catalog adb_eastus2_sandbox --source-mode postgres \
      --pg-host artemis-pg-n1.postgres.database.azure.com
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import compute, jobs
from databricks.sdk.service.workspace import ImportFormat

NOTEBOOK = Path(__file__).resolve().parent / "notebooks" / "01_zero_move_medallion.ipynb"
PG_DRIVER = "org.postgresql:postgresql:42.7.4"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="workspace host, e.g. adb-xxxx.azuredatabricks.net")
    ap.add_argument("--catalog", default="adb_eastus2_sandbox")
    ap.add_argument("--source-mode", default="postgres", choices=["postgres", "gateway"])
    ap.add_argument("--pg-host", default="artemis-pg-n1.postgres.database.azure.com")
    ap.add_argument("--gateway-url", default="")
    ap.add_argument("--secret-scope", default="artemis")
    ap.add_argument("--node-type", default="")
    args = ap.parse_args()

    w = WorkspaceClient(host=f"https://{args.host}", auth_type="azure-cli")
    me = w.current_user.me().user_name
    print(f"authenticated as {me}")

    # 1) secret scope + source credential
    scopes = [s.name for s in (w.secrets.list_scopes() or [])]
    if args.secret_scope not in scopes:
        w.secrets.create_scope(scope=args.secret_scope)
        print(f"created secret scope {args.secret_scope}")
    if args.source_mode == "postgres":
        pw = os.environ.get("PG_ADMIN_PASSWORD")
        if not pw:
            print("ERROR: set PG_ADMIN_PASSWORD for postgres mode", file=sys.stderr)
            return 2
        w.secrets.put_secret(scope=args.secret_scope, key="pg_password", string_value=pw)
        print("stored pg_password secret")

    # 2) import the notebook
    nb_path = f"/Users/{me}/artemis/01_zero_move_medallion"
    w.workspace.mkdirs(f"/Users/{me}/artemis")
    w.workspace.import_(
        path=nb_path,
        content=base64.b64encode(NOTEBOOK.read_bytes()).decode(),
        format=ImportFormat.JUPYTER,  # .ipynb — proper markdown + code cells
        overwrite=True,
    )
    print(f"imported notebook -> {nb_path}")

    # 3) submit a one-off run on a single-node UC cluster
    spark_version = w.clusters.select_spark_version(long_term_support=True)
    node_type = args.node_type or w.clusters.select_node_type(local_disk=True, min_cores=4)
    params = {"source_mode": args.source_mode, "catalog": args.catalog}
    if args.source_mode == "postgres":
        params |= {"pg_host": args.pg_host, "pg_secret_scope": args.secret_scope, "pg_secret_key": "pg_password"}
    else:
        params |= {"gateway_url": args.gateway_url, "token_secret_scope": args.secret_scope, "token_secret_key": "gateway_token"}

    print(f"submitting run (spark={spark_version}, node={node_type})...")
    run = w.jobs.submit(
        run_name="artemis-zero-move-medallion",
        tasks=[
            jobs.SubmitTask(
                task_key="medallion",
                notebook_task=jobs.NotebookTask(notebook_path=nb_path, base_parameters=params),
                new_cluster=compute.ClusterSpec(
                    spark_version=spark_version,
                    node_type_id=node_type,
                    num_workers=0,
                    data_security_mode=compute.DataSecurityMode.SINGLE_USER,
                    single_user_name=me,
                    spark_conf={"spark.master": "local[*]", "spark.databricks.cluster.profile": "singleNode"},
                    custom_tags={"ResourceClass": "SingleNode", "project": "nasa-api-first-poc"},
                ),
                libraries=[compute.Library(maven=compute.MavenLibrary(coordinates=PG_DRIVER))],
            )
        ],
    ).result()  # waits for terminal state

    state = run.state
    print(f"\nrun {run.run_id}: {state.result_state} — {state.state_message or ''}")
    print(f"run page: https://{args.host}/#job/{run.run_id}")

    # 4) validation — the notebook returns a JSON summary via dbutils.notebook.exit
    ok = str(state.result_state) == "RunResultState.SUCCESS"
    try:
        candidates = []
        if run.tasks:
            candidates.append(run.tasks[0].run_id)
        candidates.append(run.run_id)
        nb = None
        for rid in candidates:
            out = w.jobs.get_run_output(run_id=rid)
            nb = out.notebook_output.result if out.notebook_output else None
            if nb:
                break
        print(f"\nnotebook summary: {nb}")
        if nb:
            import json as _json

            s = _json.loads(nb)
            print(
                f"  -> {s.get('gold_table')}: {s.get('gold_rows')} rows; "
                f"headline={s.get('headline_rows')} ({s.get('headline_material')})"
            )
            ok = ok and s.get("headline_rows", 0) >= 1
    except Exception as exc:  # noqa: BLE001
        print(f"(could not read notebook output: {exc})")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
