#!/usr/bin/env python3
"""Generate the Artemis Supply-Chain Risk Power BI Project (PBIP) as code.

Emits a complete, source-controllable PBIP under powerbi/:
- SemanticModel in TMDL (tables, typed columns, DAX measures, DirectQuery M to a
  Databricks SQL warehouse via 3 parameters).
- Report in the enhanced PBIR format (per-visual JSON) implementing docs/POWERBI-GUIDE.md
  (4 KPI cards, program slicer, risk-tier stacked column, ranked table, vendor treemap,
  and a delay-trend line on a 2nd page).

The report binds to the model byPath. Open powerbi/ArtemisSupplyRisk.pbip in Power BI
Desktop (enable the TMDL + PBIR preview features), set the 3 parameters, authenticate to
Databricks. Data is read via DirectQuery — zero copy — the same zero-move story.

Run:  python tools/make_powerbi_pbip.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "powerbi"
MODEL_DIR = ROOT / "ArtemisSupplyRisk.SemanticModel"
REPORT_DIR = ROOT / "ArtemisSupplyRisk.Report"
NS = uuid.UUID("6f1a9c2e-0000-4a00-8a00-a17e315abc00")  # stable namespace for lineage GUIDs


def guid(key: str) -> str:
    return str(uuid.uuid5(NS, key))


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, obj: dict) -> None:
    write(path, json.dumps(obj, indent=2) + "\n")


# ───────────────────────── semantic model (TMDL) ─────────────────────────

HOST_DEFAULT = "adb-XXXXXXXXXXXXXXXX.18.azuredatabricks.net"
HTTP_PATH_DEFAULT = "/sql/1.0/warehouses/REPLACE_WITH_WAREHOUSE_ID"
CATALOG_DEFAULT = "dbw_btfabric_dev"

# (name, dataType, summarizeBy)
COLS = {
    "artemis_supply_risk": [
        ("program", "string", "none"),
        ("material_id", "string", "none"),
        ("material_name", "string", "none"),
        ("criticality", "string", "none"),
        ("sole_source", "boolean", "none"),
        ("avg_delay_days", "double", "none"),
        ("risk_score", "int64", "none"),
        ("risk_tier", "string", "none"),
        ("vendor_name", "string", "none"),
        ("cage_code", "string", "none"),
        ("past_perf_score", "double", "none"),
        ("total_committed_usd", "double", "none"),
        ("po_count", "int64", "none"),
        ("pad_anomalies", "int64", "none"),
    ],
    "delay_trend": [
        ("program", "string", "none"),
        ("order_month", "dateTime", "none"),
        ("po_count", "int64", "none"),
        ("avg_delay_days", "double", "none"),
        ("slipped_pos", "int64", "none"),
        ("committed_usd", "double", "none"),
    ],
}

# (name, DAX, formatString)
MEASURES = [
    (
        "High Risk Materials",
        "CALCULATE(COUNTROWS('artemis_supply_risk'), 'artemis_supply_risk'[risk_tier] = \"High\")",
        "#,##0",
    ),
    (
        "Critical Slips >30d",
        "CALCULATE(COUNTROWS('artemis_supply_risk'), 'artemis_supply_risk'[criticality] = \"Critical\", "
        "'artemis_supply_risk'[sole_source] = TRUE, 'artemis_supply_risk'[avg_delay_days] > 30)",
        "#,##0",
    ),
    (
        "Sole-Source Exposure ($)",
        "CALCULATE(SUM('artemis_supply_risk'[total_committed_usd]), 'artemis_supply_risk'[sole_source] = TRUE)",
        "\\$#,##0",
    ),
    ("Pad Anomalies", "SUM('artemis_supply_risk'[pad_anomalies])", "#,##0"),
    ("Avg Delay (days)", "AVERAGE('artemis_supply_risk'[avg_delay_days])", "#,##0.0"),
    ("Material Count", "COUNTROWS('artemis_supply_risk')", "#,##0"),
]


def m_partition(table: str, schema: str) -> str:
    """DirectQuery M reading one Databricks Unity Catalog table via the 3 parameters."""
    return (
        f"\t\tsource =\n"
        f"\t\t\tlet\n"
        f"\t\t\t    Source = Databricks.Catalogs(DatabricksServerHostname, DatabricksHttpPath, "
        f"[Catalog=null, Database=null, EnableAutomaticProxyDiscovery=null]),\n"
        f'\t\t\t    Catalog = Source{{[Name=CatalogName, Kind="Database"]}}[Data],\n'
        f'\t\t\t    Schema = Catalog{{[Name="{schema}", Kind="Schema"]}}[Data],\n'
        f'\t\t\t    Data = Schema{{[Name="{table}", Kind="Table"]}}[Data]\n'
        f"\t\t\tin\n"
        f"\t\t\t    Data\n"
    )


def table_tmdl(table: str) -> str:
    out = [f"table {table}", f"\tlineageTag: {guid('table:' + table)}", ""]
    for name, dtype, summ in COLS[table]:
        out += [
            f"\tcolumn {name}",
            f"\t\tdataType: {dtype}",
            f"\t\tlineageTag: {guid(f'col:{table}.{name}')}",
            f"\t\tsummarizeBy: {summ}",
            f"\t\tsourceColumn: {name}",
            "",
        ]
        if dtype == "dateTime":
            out.insert(len(out) - 1, "\t\tformatString: General Date")
    if table == "artemis_supply_risk":
        for mname, dax, fmt in MEASURES:
            out += [
                f"\tmeasure '{mname}' = {dax}",
                f"\t\tformatString: {fmt}",
                f"\t\tlineageTag: {guid('measure:' + mname)}",
                "",
            ]
    out += [
        f"\tpartition {table} = m",
        "\t\tmode: directQuery",
        m_partition(table, "gold").rstrip("\n"),
        "",
    ]
    return "\n".join(out) + "\n"


def expressions_tmdl() -> str:
    def param(name: str, value: str) -> str:
        return (
            f'expression {name} = "{value}" meta [IsParameterQuery=true, Type="Text", '
            f"IsParameterQueryRequired=true]\n"
            f"\tlineageTag: {guid('expr:' + name)}\n\n"
            f"\tannotation PBI_ResultType = Text\n"
        )

    return "\n".join(
        [
            param("DatabricksServerHostname", HOST_DEFAULT),
            param("DatabricksHttpPath", HTTP_PATH_DEFAULT),
            param("CatalogName", CATALOG_DEFAULT),
        ]
    )


def model_tmdl() -> str:
    return (
        "model Model\n"
        "\tculture: en-US\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdiscourageImplicitMeasures\n"
        "\tsourceQueryCulture: en-US\n\n"
        '\tannotation PBI_QueryOrder = ["DatabricksServerHostname","DatabricksHttpPath",'
        '"CatalogName","artemis_supply_risk","delay_trend"]\n\n'
        "ref table artemis_supply_risk\n"
        "ref table delay_trend\n"
        "ref expression DatabricksServerHostname\n"
        "ref expression DatabricksHttpPath\n"
        "ref expression CatalogName\n"
    )


def emit_semantic_model() -> None:
    write(
        MODEL_DIR / ".platform",
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "SemanticModel", "displayName": "ArtemisSupplyRisk"},
                "config": {"version": "2.0", "logicalId": guid("logical:model")},
            },
            indent=2,
        )
        + "\n",
    )
    write_json(
        MODEL_DIR / "definition.pbism",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {},
        },
    )
    write(MODEL_DIR / "definition" / "database.tmdl", "database\n\tcompatibilityLevel: 1567\n")
    write(MODEL_DIR / "definition" / "model.tmdl", model_tmdl())
    write(MODEL_DIR / "definition" / "expressions.tmdl", expressions_tmdl())
    for table in COLS:
        write(MODEL_DIR / "definition" / "tables" / f"{table}.tmdl", table_tmdl(table))


# ───────────────────────── report (PBIR) ─────────────────────────

SC = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"


def proj(table: str, prop: str, kind: str) -> dict:
    key = "Measure" if kind == "measure" else "Column"
    return {
        "field": {key: {"Expression": {"SourceRef": {"Entity": table}}, "Property": prop}},
        "queryRef": f"{table}.{prop}",
        "nativeQueryRef": prop,
    }


def visual(name: str, vtype: str, x: int, y: int, w: int, h: int, roles: dict, z: int = 0) -> dict:
    query_state = {role: {"projections": projs} for role, projs in roles.items()}
    return {
        "$schema": f"{SC}/visualContainer/1.4.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "width": w, "height": h, "z": z, "tabOrder": z},
        "visual": {
            "visualType": vtype,
            "query": {"queryState": query_state},
            "drillFilterOtherVisuals": True,
        },
    }


T = "artemis_supply_risk"
TREND = "delay_trend"

# page 1 visuals: (folder, dict)
PAGE1 = [
    (
        "kpi_high_risk",
        visual(
            "kpi_high_risk",
            "card",
            16,
            16,
            290,
            120,
            {"Values": [proj(T, "High Risk Materials", "measure")]},
            z=0,
        ),
    ),
    (
        "kpi_crit_slips",
        visual(
            "kpi_crit_slips",
            "card",
            322,
            16,
            290,
            120,
            {"Values": [proj(T, "Critical Slips >30d", "measure")]},
            z=1,
        ),
    ),
    (
        "kpi_sole_exposure",
        visual(
            "kpi_sole_exposure",
            "card",
            628,
            16,
            290,
            120,
            {"Values": [proj(T, "Sole-Source Exposure ($)", "measure")]},
            z=2,
        ),
    ),
    (
        "kpi_pad_anomalies",
        visual(
            "kpi_pad_anomalies",
            "card",
            934,
            16,
            290,
            120,
            {"Values": [proj(T, "Pad Anomalies", "measure")]},
            z=3,
        ),
    ),
    (
        "slicer_program",
        visual(
            "slicer_program",
            "slicer",
            934,
            152,
            290,
            160,
            {"Values": [proj(T, "program", "column")]},
            z=4,
        ),
    ),
    (
        "bar_risk_by_program",
        visual(
            "bar_risk_by_program",
            "stackedColumnChart",
            16,
            152,
            590,
            264,
            {
                "Category": [proj(T, "program", "column")],
                "Series": [proj(T, "risk_tier", "column")],
                "Y": [proj(T, "Material Count", "measure")],
            },
            z=5,
        ),
    ),
    (
        "treemap_vendor_exposure",
        visual(
            "treemap_vendor_exposure",
            "treemap",
            620,
            152,
            298,
            264,
            {
                "Group": [proj(T, "vendor_name", "column")],
                "Values": [proj(T, "Sole-Source Exposure ($)", "measure")],
            },
            z=6,
        ),
    ),
    (
        "table_ranked_parts",
        visual(
            "table_ranked_parts",
            "tableEx",
            16,
            428,
            1208,
            276,
            {
                "Values": [
                    proj(T, "material_name", "column"),
                    proj(T, "vendor_name", "column"),
                    proj(T, "risk_tier", "column"),
                    proj(T, "risk_score", "column"),
                    proj(T, "avg_delay_days", "column"),
                    proj(T, "total_committed_usd", "column"),
                ]
            },
            z=7,
        ),
    ),
]

PAGE2 = [
    (
        "slicer_program_trend",
        visual(
            "slicer_program_trend",
            "slicer",
            16,
            16,
            290,
            150,
            {"Values": [proj(TREND, "program", "column")]},
            z=0,
        ),
    ),
    (
        "line_delay_trend",
        visual(
            "line_delay_trend",
            "lineChart",
            16,
            180,
            1208,
            520,
            {
                "Category": [proj(TREND, "order_month", "column")],
                "Series": [proj(TREND, "program", "column")],
                "Y": [
                    proj(TREND, "avg_delay_days", "column"),
                    proj(TREND, "slipped_pos", "column"),
                ],
            },
            z=1,
        ),
    ),
]

PAGES = [
    ("overview", "Artemis Supply-Chain Risk", PAGE1),
    ("delay_trend", "Delay Trend", PAGE2),
]


def emit_report() -> None:
    write(
        REPORT_DIR / ".platform",
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "Report", "displayName": "ArtemisSupplyRisk"},
                "config": {"version": "2.0", "logicalId": guid("logical:report")},
            },
            indent=2,
        )
        + "\n",
    )
    write_json(
        REPORT_DIR / "definition.pbir",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byPath": {"path": "../ArtemisSupplyRisk.SemanticModel"}},
        },
    )
    d = REPORT_DIR / "definition"
    write_json(
        d / "version.json",
        {"$schema": f"{SC}/versionMetadata/1.0.0/schema.json", "version": "1.0.0"},
    )
    write_json(
        d / "report.json",
        {
            "$schema": f"{SC}/report/1.0.0/schema.json",
            "layoutOptimization": "None",
            "themeCollection": {
                "baseTheme": {
                    "name": "CY24SU10",
                    "reportVersionAtImport": "5.61",
                    "type": "SharedResources",
                }
            },
        },
    )
    write_json(
        d / "pages" / "pages.json",
        {
            "$schema": f"{SC}/pagesMetadata/1.0.0/schema.json",
            "pageOrder": [p[0] for p in PAGES],
            "activePageName": PAGES[0][0],
        },
    )
    for pname, disp, visuals in PAGES:
        write_json(
            d / "pages" / pname / "page.json",
            {
                "$schema": f"{SC}/page/1.4.0/schema.json",
                "name": pname,
                "displayName": disp,
                "displayOption": "FitToPage",
                "width": 1280,
                "height": 720,
            },
        )
        for vname, vobj in visuals:
            write_json(d / "pages" / pname / "visuals" / vname / "visual.json", vobj)


def emit_pbip() -> None:
    write_json(
        ROOT / "ArtemisSupplyRisk.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/pbip/definitionProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": "ArtemisSupplyRisk.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )


def main() -> None:
    emit_semantic_model()
    emit_report()
    emit_pbip()
    n = sum(1 for _ in ROOT.rglob("*") if _.is_file())
    print(f"Wrote {n} PBIP files under {ROOT}")


if __name__ == "__main__":
    main()
