-- Databricks SQL — sample queries against the Unity Catalog gold mart built by
-- notebooks/01_zero_move_medallion.ipynb. Run these in a Databricks SQL warehouse;
-- they are also the basis for the Power BI report (docs/POWERBI-GUIDE.md).
--
-- Set the catalog to the one the notebook wrote to (run_notebook.py --catalog;
-- the reference workspace uses main). The queries below are then
-- catalog-relative, so you only change this one line for your environment.
USE CATALOG main;   -- <-- change to your Unity Catalog

-- 1) The headline mission question (the same answer the CLI/MCP/UI return, now in DBSQL):
SELECT program, material_name, vendor_name, risk_tier, risk_score, avg_delay_days, total_committed_usd
FROM gold.artemis_supply_risk
WHERE program = 'Artemis-3' AND criticality = 'Critical' AND sole_source = TRUE
  AND avg_delay_days > 30
ORDER BY risk_score DESC;

-- 2) Risk distribution by program (Power BI: stacked bar):
SELECT program, risk_tier, COUNT(*) AS materials, ROUND(AVG(avg_delay_days), 1) AS avg_delay
FROM gold.artemis_supply_risk
GROUP BY program, risk_tier
ORDER BY program, risk_tier;

-- 3) Top sole-source exposure by committed value (Power BI: table / treemap):
SELECT vendor_name, cage_code, COUNT(*) AS materials,
       SUM(total_committed_usd) AS committed_usd, MAX(risk_score) AS top_risk
FROM gold.artemis_supply_risk
WHERE sole_source = TRUE
GROUP BY vendor_name, cage_code
ORDER BY committed_usd DESC
LIMIT 15;

-- 4) Launch-pad anomaly impact (Power BI: KPI card):
SELECT COUNT(*) AS impacted_materials, SUM(pad_anomalies) AS total_pad_anomalies
FROM gold.artemis_supply_risk
WHERE pad_anomalies > 0;

-- 5) Monthly delay trend by program (Power BI: line chart — from gold.delay_trend):
SELECT program, order_month, po_count, avg_delay_days, slipped_pos, committed_usd
FROM gold.delay_trend
ORDER BY order_month, program;
