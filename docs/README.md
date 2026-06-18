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
| [`DEMO-DAY.md`](DEMO-DAY.md) | **Full end-to-end runbook** (local → Azure → APIM → Databricks → Power BI) |
| [`DEMO-SCRIPT.md`](DEMO-SCRIPT.md) | ~10-minute local presenter walkthrough |
| [`DISCLAIMER.md`](DISCLAIMER.md) | Legal notice + synthetic-data statement |

## 🔧 Build & run the pattern

| Doc | What it covers |
|---|---|
| [`ZERO-MOVE.md`](ZERO-MOVE.md) | How zero-move is *proven* (network isolation + tests) |
| [`SECURITY.md`](SECURITY.md) | Token flow + OWASP API Top 10 controls at the gateway |
| [`ADD-A-SOURCE.md`](ADD-A-SOURCE.md) | Publish a new source through the gateway (UI wizard + API) |
| [`GRAPHQL.md`](GRAPHQL.md) | Query the same auto-API as GraphQL through the gateway (multi-model) |

## 🌐 Extend to Azure & analytics

| Doc | What it covers |
|---|---|
| [`AZURE-DEPLOYMENT.md`](AZURE-DEPLOYMENT.md) | Managed-target mapping + reference Bicep |
| [`AZURE-LIVE-DEPLOYMENT.md`](AZURE-LIVE-DEPLOYMENT.md) | The live, tenant-locked Container Apps deploy (Kong edition) |
| [`APIM-EDITION.md`](APIM-EDITION.md) | Managed-gateway edition: APIM deploy + Developer Portal + two-version comparison |
| [`APIM-CAPABILITIES.md`](APIM-CAPABILITIES.md) | What managed Azure API Management adds over the OSS gateway |
| [`DATABRICKS-WALKTHROUGH.md`](DATABRICKS-WALKTHROUGH.md) | Zero-move medallion → Unity Catalog → Databricks SQL |
| [`POWERBI-GUIDE.md`](POWERBI-GUIDE.md) | Connect Power BI to the Gold mart + report spec |

![Architecture](architecture.png)
