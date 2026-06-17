# Azure deployment path (reference)

The local POC promotes to Azure by swapping each open-source/local component for its
managed equivalent. CI does **not** require an Azure subscription — `infra/azure/`
(Bicep) and this doc are reference material.

## Component swaps

| POC (local) | Azure managed target | Notes |
|---|---|---|
| Kong Gateway OSS | **Azure API Management** | Map the same JWT/rate-limit/metering policies; APIM's AI gateway adds `llm-token-limit` / `llm-emit-token-metric` for the LLM-gateway story. |
| Local OIDC/JWT issuer | **Microsoft Entra ID** | `validate-azure-ad-token`; identity is the moat under every layer. |
| Data API Builder (container) | **Data API Builder on Azure Container Apps**, or **Dataverse Web API** | Dataverse exposes OData v4 with `$metadata` discovery. |
| PostgreSQL | **Azure Database for PostgreSQL Flexible Server** / **Azure SQL** | The system of record. |
| `classification.yml` | **Microsoft Purview** | Catalog, classification, sensitivity labels, lineage, data quality. |
| Prometheus / Grafana | **Azure Monitor / Log Analytics / Application Insights** | Per-consumer metrics + tracing. |

## Data platform (posture for this customer)

The managed data platform — **Azure Databricks with managed Unity Catalog, Databricks
SQL, Delta Lake, and Delta Sharing on ADLS Gen2, plus Azure Synapse** — runs in
**commercial (global) Azure at FedRAMP High** (the boundary the customer's cyber org
has accepted for Databricks). The full *managed* platform is available there.

- **Data classification drives the boundary**, not vendor preference: unclassified /
  CUI-adjacent workloads run in commercial Azure at FedRAMP High.
- The managed-Unity-Catalog / Databricks-SQL gap applies **only** to the Azure
  Government regions (US Gov Arizona / US Gov Virginia) — an **ITAR / strict-CUI
  subset** — where open-source Unity Catalog on agency-controlled compute or Microsoft
  Purview is the catalog fallback.
- Open formats (Delta Lake / Delta Sharing) and the open-source-rooted Unity Catalog
  keep the platform **divestable** either way.
- **Microsoft Fabric and OneLake are excluded** — not available in Azure Government /
  GCC. Do not introduce them.

## Compliance

Both global Azure and Azure Government hold FedRAMP High authorization; the practical
difference is data residency and personnel-access controls (ITAR/EAR), not the FedRAMP
level. See the Technical Companion (`docs/whitepapers/02_technical_api_first_companion.md`)
for the full FedRAMP High / Azure Government / GCC discussion.

> _Fill in the Bicep specifics under `infra/azure/` during the build (PRP §12)._
