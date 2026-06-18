# Documentation index

[Home](../README.md) > **Documentation**

> [!WARNING]
> **Illustrative reference · sample/synthetic data only · not an official NASA
> document.** See **[DISCLAIMER.md](DISCLAIMER.md)** before sharing or adapting.

A generic NASA-mission use case for an **API-first, zero-move, multi-source data
marketplace** — and the runnable proof in this repo.

## 🚀 Start here

| Doc | What it covers |
|---|---|
| [`../README.md`](../README.md) | Quickstart, what it demonstrates, repo layout |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Components, zero-move flow, Azure↔OSS mapping, federation + control-plane |
| [`DEMO-SCRIPT.md`](DEMO-SCRIPT.md) | ~10-minute live presenter walkthrough |
| [`DISCLAIMER.md`](DISCLAIMER.md) | Legal notice + synthetic-data statement |

## 🔧 Build & run the pattern

| Doc | What it covers |
|---|---|
| [`ZERO-MOVE.md`](ZERO-MOVE.md) | How zero-move is *proven* (network isolation + tests) |
| [`SECURITY.md`](SECURITY.md) | Token flow + OWASP API Top 10 controls at the gateway |
| [`ADD-A-SOURCE.md`](ADD-A-SOURCE.md) | Publish a new source through the gateway (UI wizard + API) |

## 🌐 Extend to Azure & analytics

| Doc | What it covers |
|---|---|
| [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md) | Managed-target mapping + reference Bicep |
| [`AZURE-LIVE-DEPLOYMENT.md`](AZURE-LIVE-DEPLOYMENT.md) | The live, tenant-locked Container Apps deploy (Kong edition) |
| [`APIM-EDITION.md`](APIM-EDITION.md) | Managed-gateway edition: APIM deploy + Developer Portal + two-version comparison |
| [`APIM-CAPABILITIES.md`](APIM-CAPABILITIES.md) | What managed Azure API Management adds over the OSS gateway |
| [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md) | Zero-move medallion → Unity Catalog → Databricks SQL |
| [`POWERBI-GUIDE.md`](POWERBI-GUIDE.md) | Connect Power BI to the Gold mart + report spec |

## 📝 Program narrative (illustrative whitepapers)

Generic, de-identified papers framing the use case — **not** an official NASA deliverable;
all scenarios use synthetic data. See [`whitepapers/`](whitepapers/):

1. [Executive Concept Paper](whitepapers/01_executive_concept_paper.md) — one platform for data, APIs, and code
2. [Technical Companion](whitepapers/02_technical_api_first_companion.md) — APIM, Dataverse, Azure AI as connective tissue
3. [Artemis Worked Example](whitepapers/03_artemis_worked_example.md) — synthetic SAP procurement → governed API
4. [Resourcing Framework](whitepapers/04_resourcing_framework.md) — capability/staffing-pattern model
5. [Pre-Read Brief](whitepapers/05_preread.md) — short framing brief
6. [Administrator Brief](whitepapers/06_administrator_leave_behind.md) — one-page summary

![Architecture](architecture.png)
