# Databricks notebook source
# MAGIC %md
# MAGIC # Zero-move ingestion → medallion (Bronze → Silver → Gold) in Unity Catalog
# MAGIC
# MAGIC This notebook consumes the **API-first data marketplace** *through the governed
# MAGIC gateway* — never the source database. It lands the responses as **Delta** in
# MAGIC **Unity Catalog** (Bronze), refines to **Silver**, builds a **Gold** supply-risk
# MAGIC mart, and leaves everything queryable from a **Databricks SQL warehouse** (and
# MAGIC therefore Power BI).
# MAGIC
# MAGIC **Zero-move:** the system of record stays put; Databricks reads the *data product*
# MAGIC over the metered, authenticated API (the same surface the CLI/MCP/UI use), so
# MAGIC access is governed and auditable — not a bulk database copy.
# MAGIC
# MAGIC Synthetic data only (ITAR/CUI-safe).

# COMMAND ----------
# MAGIC %md ## Parameters
# MAGIC Point at the gateway and supply a bearer token. Locally: the Kong gateway + the
# MAGIC RS256 issuer. In Azure: the API Management / Container Apps URL + an Entra token
# MAGIC (store the token in a Databricks secret scope, never inline).

dbutils.widgets.dropdown("source_mode", "postgres", ["gateway", "postgres"], "Source mode")
dbutils.widgets.text("gateway_url", "http://localhost:8000", "Gateway base URL")
dbutils.widgets.text("identity_url", "http://localhost:8081", "Identity issuer URL (local)")
dbutils.widgets.text("consumer", "artemis-agent", "Consumer id")
dbutils.widgets.text("catalog", "artemis", "Unity Catalog name")
dbutils.widgets.text("token_secret_scope", "", "Secret scope holding a bearer token (Azure)")
dbutils.widgets.text("token_secret_key", "", "Secret key for the bearer token (Azure)")
# postgres mode (run TODAY against the deployed cloud SoR — reachable from the workspace):
dbutils.widgets.text("pg_host", "artemis-pg-n1.postgres.database.azure.com", "Postgres host")
dbutils.widgets.text("pg_secret_scope", "artemis", "Secret scope with the PG password")
dbutils.widgets.text("pg_secret_key", "pg_password", "Secret key for the PG password")

SOURCE_MODE = dbutils.widgets.get("source_mode")
GATEWAY = dbutils.widgets.get("gateway_url").rstrip("/")
IDENTITY = dbutils.widgets.get("identity_url").rstrip("/")
CONSUMER = dbutils.widgets.get("consumer")
CATALOG = dbutils.widgets.get("catalog")
SCOPE = dbutils.widgets.get("token_secret_scope")
KEY = dbutils.widgets.get("token_secret_key")
PG_HOST = dbutils.widgets.get("pg_host")
PG_SCOPE = dbutils.widgets.get("pg_secret_scope")
PG_KEY = dbutils.widgets.get("pg_secret_key")

# COMMAND ----------
# MAGIC %md ## Get a bearer token (governed access)

import json
import urllib.parse
import urllib.request


def get_token() -> str:
    # Azure: read an Entra token from a Databricks secret scope.
    if SCOPE and KEY:
        return dbutils.secrets.get(SCOPE, KEY)
    # Local demo: the RS256 issuer mints a per-consumer token.
    req = urllib.request.Request(
        f"{IDENTITY}/token",
        data=json.dumps({"consumer": CONSUMER}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["access_token"]


def gateway_get(path: str, token: str) -> list[dict]:
    url = f"{GATEWAY}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        corr = r.headers.get("X-Correlation-ID")
        body = json.loads(r.read())
    print(f"GET {path} -> {len(body.get('value', []))} rows (gateway corr-id {corr})")
    return body.get("value", [])


TOKEN = get_token()
print("token acquired:", bool(TOKEN))

# COMMAND ----------
# MAGIC %md ## Unity Catalog: catalog + medallion schemas

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
for layer in ("bronze", "silver", "gold"):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{layer}")
spark.sql(f"USE CATALOG {CATALOG}")
print("Unity Catalog ready:", CATALOG)

# COMMAND ----------
# MAGIC %md ## Bronze — land the raw data product as Delta
# MAGIC - **gateway** mode: read each data product *through the governed gateway* (the
# MAGIC   zero-move-via-API story; needs the gateway reachable from the workspace + a token).
# MAGIC - **postgres** mode: read the deployed cloud system-of-record over JDBC (runs TODAY
# MAGIC   in your workspace against the live Azure Postgres). Set a secret with the password.

from pyspark.sql import functions as F


def land(df, table: str) -> None:
    (
        df.withColumn("_ingested_at", F.current_timestamp())
        .write.format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(f"{CATALOG}.bronze.{table}")
    )
    print(f"  bronze.{table}: {df.count()} rows")


if SOURCE_MODE == "gateway":
    SOURCES = [
        ("/api/Material?$first=200", "materials"),
        ("/api/Vendor?$first=200", "vendors"),
        ("/api/PurchaseOrder?$first=200", "purchase_orders"),
        ("/api/SupplyRisk?$first=200", "supply_risk"),
        ("/dot/api/Bridge?$first=200", "dot_bridges"),  # federated 2nd source (optional)
    ]
    for path, table in SOURCES:
        try:
            rows = gateway_get(path, TOKEN)
        except Exception as exc:
            print(f"  skip {table}: {exc}")
            continue
        if rows:
            land(spark.createDataFrame(rows), table)
else:  # postgres — direct JDBC read of the deployed cloud SoR
    pg_pw = dbutils.secrets.get(PG_SCOPE, PG_KEY)
    jdbc = f"jdbc:postgresql://{PG_HOST}:5432/procurement?sslmode=require"
    props = {"user": "artemis", "password": pg_pw, "driver": "org.postgresql.Driver"}
    for table in ("vendors", "materials", "purchase_orders", "supply_risk"):
        land(spark.read.jdbc(jdbc, table, properties=props), table)

# COMMAND ----------
# MAGIC %md ## Silver — typed, cleaned, conformed

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.silver.supply_risk AS
SELECT
  CAST(matnr AS STRING)            AS material_id,
  CAST(maktx AS STRING)            AS material_name,
  CAST(program AS STRING)          AS program,
  CAST(criticality AS STRING)      AS criticality,
  CAST(sole_source AS BOOLEAN)     AS sole_source,
  CAST(po_count AS INT)            AS po_count,
  CAST(late_po_count AS INT)       AS late_po_count,
  CAST(avg_delay_days AS DOUBLE)   AS avg_delay_days,
  CAST(risk_score AS INT)          AS risk_score,
  CAST(risk_tier AS STRING)        AS risk_tier
FROM {CATALOG}.bronze.supply_risk
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.silver.purchase_orders AS
SELECT
  CAST(ebeln AS STRING) AS po_number,
  CAST(matnr AS STRING) AS material_id,
  CAST(lifnr AS BIGINT) AS vendor_id,
  CAST(program AS STRING) AS program,
  CAST(criticality AS STRING) AS criticality,
  CAST(netwr AS DOUBLE) AS net_value_usd,
  CAST(delay_days AS INT) AS delay_days,
  CAST(pad_anomaly AS BOOLEAN) AS pad_anomaly,
  CAST(status AS STRING) AS status
FROM {CATALOG}.bronze.purchase_orders
""")

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.silver.vendors AS
SELECT
  CAST(lifnr AS BIGINT) AS vendor_id,
  CAST(name1 AS STRING) AS vendor_name,
  CAST(cage_code AS STRING) AS cage_code,
  CAST(sole_source AS BOOLEAN) AS sole_source,
  CAST(past_perf_score AS DOUBLE) AS past_perf_score,
  CAST(small_business AS BOOLEAN) AS small_business
FROM {CATALOG}.bronze.vendors
""")
print("silver tables built")

# COMMAND ----------
# MAGIC %md ## Gold — the supply-risk mart Power BI reads (materials × suppliers × risk)

spark.sql(f"""
CREATE OR REPLACE TABLE {CATALOG}.gold.artemis_supply_risk AS
SELECT
  r.program,
  r.material_id,
  r.material_name,
  r.criticality,
  r.sole_source,
  r.avg_delay_days,
  r.risk_score,
  r.risk_tier,
  v.vendor_name,
  v.cage_code,
  v.past_perf_score,
  COALESCE(p.total_value_usd, 0) AS total_committed_usd,
  COALESCE(p.po_count, 0)        AS po_count,
  COALESCE(p.pad_anomalies, 0)   AS pad_anomalies
FROM {CATALOG}.silver.supply_risk r
LEFT JOIN (
  SELECT material_id,
         MAX(vendor_id) AS vendor_id,
         SUM(net_value_usd) AS total_value_usd,
         COUNT(*) AS po_count,
         SUM(CASE WHEN pad_anomaly THEN 1 ELSE 0 END) AS pad_anomalies
  FROM {CATALOG}.silver.purchase_orders GROUP BY material_id
) p ON r.material_id = p.material_id
LEFT JOIN {CATALOG}.silver.vendors v ON p.vendor_id = v.vendor_id
""")

# Comment the gold table for discoverability in Unity Catalog / Databricks SQL.
spark.sql(f"COMMENT ON TABLE {CATALOG}.gold.artemis_supply_risk IS "
          "'Synthetic Artemis supply-risk mart (gateway-sourced; zero-move). For Power BI / DBSQL.'")

display(spark.sql(f"""
  SELECT program, material_name, vendor_name, risk_tier, risk_score, avg_delay_days
  FROM {CATALOG}.gold.artemis_supply_risk
  WHERE program = 'Artemis-3' AND criticality = 'Critical' AND sole_source = true
    AND avg_delay_days > 30
  ORDER BY risk_score DESC
"""))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Done
# MAGIC - `artemis.gold.artemis_supply_risk` is the curated mart for Databricks SQL / Power BI.
# MAGIC - Connect Power BI to the SQL warehouse and import this table — see
# MAGIC   `docs/POWERBI-GUIDE.md`. Delta Sharing can publish `gold` to external consumers
# MAGIC   without copying (the zero-move story, extended to analytics).
