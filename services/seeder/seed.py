"""Seed Postgres with the synthetic Artemis SAP-procurement data.

Pipeline (the "classify BEFORE exposure" discipline):
  1. generate the deterministic CSVs via data/synthetic_data.py (seed=42),
  2. apply schema.sql (idempotent DROP+CREATE),
  3. load the four tables with proper typing,
  4. stamp each table/column with its sensitivity label from classification.yml as a
     Postgres COMMENT (so the label travels with the system of record), and
  5. print a summary + the known high-risk Artemis-3 rows.

Runs as a one-shot job (compose `seeder` service / `make seed`). DAB starts only after
this completes, so the auto-API has a schema to reflect.
"""

from __future__ import annotations

import csv
import logging
import os
import sys
import time
from datetime import date
from pathlib import Path

import psycopg
import yaml
from psycopg import sql
from synthetic_data import generate_artemis_procurement

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("seeder")

APP_DIR = Path(__file__).resolve().parent
SCHEMA_SQL = APP_DIR / "schema.sql"
CLASSIFICATION_YML = APP_DIR / "classification.yml"
OUT_DIR = Path(os.environ.get("SEED_OUT_DIR", "/tmp/artemis_out"))
SEED = int(os.environ.get("SYNTHETIC_SEED", "42"))


def _bool(v: str) -> bool:
    return str(v).strip().upper() == "X"


def _date(v: str):
    return date.fromisoformat(v) if v else None


def _int(v: str):
    return int(v) if v not in ("", None) else None


def _num(v: str):
    return float(v) if v not in ("", None) else None


def _text(v: str):
    return v if v != "" else None


# CSV file -> (table, ordered [(db_column, csv_header, converter)])
TABLES = {
    "vendors": (
        "artemis_vendors.csv",
        [
            ("lifnr", "LIFNR", _int),
            ("name1", "NAME1", _text),
            ("cage_code", "CAGE_CODE", _text),
            ("regio", "REGIO", _text),
            ("land1", "LAND1", _text),
            ("sole_source", "SOLE_SOURCE", _bool),
            ("past_perf_score", "PAST_PERF_SCORE", _num),
            ("small_business", "SMALL_BUSINESS", _bool),
        ],
    ),
    "materials": (
        "artemis_materials.csv",
        [
            ("matnr", "MATNR", _text),
            ("maktx", "MAKTX", _text),
            ("matkl", "MATKL", _text),
            ("program", "PROGRAM", _text),
            ("criticality", "CRITICALITY", _text),
            ("std_lead_time_days", "STD_LEAD_TIME_DAYS", _int),
            ("std_unit_cost_usd", "STD_UNIT_COST_USD", _num),
            ("uom", "UOM", _text),
        ],
    ),
    "purchase_orders": (
        "artemis_purchase_orders.csv",
        [
            ("ebeln", "EBELN", _text),
            ("ebelp", "EBELP", _text),
            ("matnr", "MATNR", _text),
            ("maktx", "MAKTX", _text),
            ("lifnr", "LIFNR", _int),
            ("program", "PROGRAM", _text),
            ("criticality", "CRITICALITY", _text),
            ("menge", "MENGE", _int),
            ("meins", "MEINS", _text),
            ("netpr", "NETPR", _num),
            ("netwr", "NETWR", _num),
            ("waers", "WAERS", _text),
            ("eindt", "EINDT", _date),
            ("bedat", "BEDAT", _date),
            ("actual_delivery", "ACTUAL_DELIVERY", _date),
            ("delay_days", "DELAY_DAYS", _int),
            ("pad_anomaly", "PAD_ANOMALY", _bool),
            ("status", "STATUS", _text),
        ],
    ),
    "supply_risk": (
        "artemis_supply_risk.csv",
        [
            ("matnr", "MATNR", _text),
            ("maktx", "MAKTX", _text),
            ("program", "PROGRAM", _text),
            ("criticality", "CRITICALITY", _text),
            ("sole_source", "SOLE_SOURCE", _bool),
            ("po_count", "PO_COUNT", _int),
            ("late_po_count", "LATE_PO_COUNT", _int),
            ("avg_delay_days", "AVG_DELAY_DAYS", _num),
            ("risk_score", "RISK_SCORE", _int),
            ("risk_tier", "RISK_TIER", _text),
        ],
    ),
}


def connect_with_retry(dsn: str, attempts: int = 30, delay: float = 2.0) -> psycopg.Connection:
    last: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return psycopg.connect(dsn)
        except psycopg.OperationalError as exc:
            last = exc
            log.info("postgres not ready (attempt %s/%s): %s", i, attempts, exc)
            time.sleep(delay)
    raise SystemExit(f"could not connect to postgres after {attempts} attempts: {last}")


def dsn_from_env() -> str:
    return (
        f"host={os.environ.get('POSTGRES_HOST', 'postgres')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'procurement')} "
        f"user={os.environ.get('POSTGRES_USER', 'artemis')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'artemis_local_demo')}"
    )


def load_table(cur: psycopg.Cursor, table: str, csv_path: Path, cols: list) -> int:
    db_cols = [c[0] for c in cols]
    placeholders = ", ".join(["%s"] * len(db_cols))
    insert = f"INSERT INTO {table} ({', '.join(db_cols)}) VALUES ({placeholders})"
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            rows.append(tuple(conv(rec[hdr]) for (_db, hdr, conv) in cols))
    cur.executemany(insert, rows)
    return len(rows)


def apply_classification(cur: psycopg.Cursor) -> int:
    if not CLASSIFICATION_YML.exists():
        log.warning("no classification.yml found; skipping labels")
        return 0
    manifest = yaml.safe_load(CLASSIFICATION_YML.read_text(encoding="utf-8"))
    applied = 0
    for table, spec in (manifest.get("tables") or {}).items():
        label = spec.get("label", manifest.get("default_label", "Routine"))
        cur.execute(
            sql.SQL("COMMENT ON TABLE {} IS {}").format(
                sql.Identifier(table), sql.Literal(f"Sensitivity: {label}")
            )
        )
        applied += 1
        for col, col_label in (spec.get("columns") or {}).items():
            cur.execute(
                sql.SQL("COMMENT ON COLUMN {}.{} IS {}").format(
                    sql.Identifier(table),
                    sql.Identifier(col.lower()),
                    sql.Literal(f"Sensitivity: {col_label}"),
                )
            )
            applied += 1
    return applied


def main() -> int:
    log.info("generating synthetic Artemis dataset (seed=%s) -> %s", SEED, OUT_DIR)
    result = generate_artemis_procurement(OUT_DIR, seed=SEED)
    log.info("generated counts: %s", result["counts"])

    dsn = dsn_from_env()
    conn = connect_with_retry(dsn)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            log.info("applying schema.sql")
            cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))

            counts = {}
            for table, (fname, cols) in TABLES.items():
                n = load_table(cur, table, OUT_DIR / fname, cols)
                counts[table] = n
                log.info("loaded %s rows into %s", n, table)

            labels = apply_classification(cur)
            log.info("applied %s sensitivity labels (table + column comments)", labels)

            # surface the headline answer straight from the SoR as a sanity check
            cur.execute(
                """
                SELECT matnr, maktx, risk_score, avg_delay_days
                FROM supply_risk
                WHERE program = 'Artemis-3' AND criticality = 'Critical'
                  AND sole_source = TRUE AND avg_delay_days > 30
                ORDER BY risk_score DESC
                """
            )
            headline = cur.fetchall()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    log.info("row counts: %s", counts)
    log.info("Artemis-3 Critical sole-source >30d slips (from SoR): %s", headline)
    print("\n=== Seed complete (synthetic data; classify-before-exposure applied) ===")
    for t, n in counts.items():
        print(f"  {t:16s} {n:>4d} rows")
    print(f"  headline high-risk rows: {len(headline)} -> {headline}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
