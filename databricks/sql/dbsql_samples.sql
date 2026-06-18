-- Databricks SQL — sample queries against the Unity Catalog gold mart built by
-- notebooks/01_zero_move_medallion.py. Run these in a Databricks SQL warehouse;
-- they are also the basis for the Power BI report (docs/POWERBI-GUIDE.md).

-- 1) The headline mission question (the same answer the CLI/MCP/UI return, now in DBSQL):
SELECT program, material_name, vendor_name, risk_tier, risk_score, avg_delay_days, total_committed_usd
FROM artemis.gold.artemis_supply_risk
WHERE program = 'Artemis-3' AND criticality = 'Critical' AND sole_source = TRUE
  AND avg_delay_days > 30
ORDER BY risk_score DESC;

-- 2) Risk distribution by program (Power BI: stacked bar):
SELECT program, risk_tier, COUNT(*) AS materials, ROUND(AVG(avg_delay_days), 1) AS avg_delay
FROM artemis.gold.artemis_supply_risk
GROUP BY program, risk_tier
ORDER BY program, risk_tier;

-- 3) Top sole-source exposure by committed value (Power BI: table / treemap):
SELECT vendor_name, cage_code, COUNT(*) AS materials,
       SUM(total_committed_usd) AS committed_usd, MAX(risk_score) AS top_risk
FROM artemis.gold.artemis_supply_risk
WHERE sole_source = TRUE
GROUP BY vendor_name, cage_code
ORDER BY committed_usd DESC
LIMIT 15;

-- 4) Launch-pad anomaly impact (Power BI: KPI card):
SELECT COUNT(*) AS impacted_materials, SUM(pad_anomalies) AS total_pad_anomalies
FROM artemis.gold.artemis_supply_risk
WHERE pad_anomalies > 0;
