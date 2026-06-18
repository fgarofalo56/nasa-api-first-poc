# Power BI — supply-risk report on the Databricks Gold mart

Connect Power BI to the Databricks SQL warehouse and build a supply-risk report on
`artemis.gold.artemis_supply_risk` (built by `databricks/notebooks/01_zero_move_medallion.py`).

> **Why this is still zero-move:** use **DirectQuery** — Power BI queries the Delta mart
> in place through the SQL warehouse; the data stays in the lakehouse. (Import mode caches
> a copy in the PBIX; choose per governance needs.)

> **Note on automation:** a finished `.pbix` is a GUI artifact and isn't generated
> headlessly — this is the build spec (connection + model + measures + visuals) a
> presenter follows in Power BI Desktop. Everything upstream (Delta, Unity Catalog, the
> SQL queries) is fully built in this repo.

## 1. Connect

Power BI Desktop → **Get Data → Azure Databricks**:
- **Server hostname** and **HTTP path** — from the SQL warehouse's *Connection details*.
- **Authentication:** Microsoft Entra ID (sign in with a tenant account — same tenant
  lock as the rest of the demo).
- **Data Connectivity mode:** **DirectQuery** (recommended) or Import.

Navigator → expand `artemis` → `gold` → select **`artemis_supply_risk`** → Load.

## 2. Measures (DAX)

```DAX
High Risk Materials = CALCULATE(COUNTROWS('artemis_supply_risk'), 'artemis_supply_risk'[risk_tier] = "High")
Sole-Source Exposure ($) = CALCULATE(SUM('artemis_supply_risk'[total_committed_usd]), 'artemis_supply_risk'[sole_source] = TRUE)
Avg Delay (days) = AVERAGE('artemis_supply_risk'[avg_delay_days])
Pad Anomalies = SUM('artemis_supply_risk'[pad_anomalies])
Critical Slips >30d =
CALCULATE(
    COUNTROWS('artemis_supply_risk'),
    'artemis_supply_risk'[criticality] = "Critical",
    'artemis_supply_risk'[sole_source] = TRUE,
    'artemis_supply_risk'[avg_delay_days] > 30
)
```

## 3. Report layout (one page, "Artemis Supply-Chain Risk")

| Visual | Field(s) | Purpose |
|---|---|---|
| KPI cards (4) | `High Risk Materials`, `Critical Slips >30d`, `Sole-Source Exposure ($)`, `Pad Anomalies` | the headline numbers |
| Slicer | `program` (default **Artemis-3**) | mission filter |
| Stacked bar | axis `program`, legend `risk_tier`, value `COUNTROWS` | risk distribution |
| Table | `material_name`, `vendor_name`, `risk_tier`, `risk_score`, `avg_delay_days`, `total_committed_usd` | the ranked at-risk parts + suppliers |
| Treemap | group `vendor_name`, value `Sole-Source Exposure ($)` | concentration of single-source spend |

Conditional formatting: color `risk_tier` (High = red `#FC3D21`, Medium = amber, Low =
green) to match the marketplace UI.

## 4. Publish (optional)

**Publish** to a Power BI Service workspace in the tenant; set the Databricks data source
credentials (Entra) in the dataset settings. Row-level security and sensitivity labels
(Microsoft Purview) extend the classify-before-exposure discipline to the report layer.

## 5. The narrative for the customer

> "The same supply-risk answer the gateway serves — `Mobile launcher umbilical`, risk 99,
> 34.8-day average slip — now lands in the lakehouse via a governed, metered read, is
> curated in Unity Catalog, and is presented in Power BI over DirectQuery. One data
> product, consumed by a CLI, an MCP agent, the marketplace UI, **and** the analytics
> platform — without copying the system of record."
