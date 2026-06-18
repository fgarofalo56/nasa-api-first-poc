# Azure live deployment (limitlessdata tenant)

A **functional** deployment of the auto-API over a managed system of record, **locked to
the tenant** with Microsoft Entra built-in authentication — the same pattern as the
`azure-dab-fullstack-demo` (DOT) app. Reproduce with `scripts/azure-deploy.sh`
(`PG_ADMIN_PASSWORD` from the environment; no secrets in the repo).

## What is deployed

| Resource | Name | Notes |
|---|---|---|
| Resource group | `artemis-poc-rg` (Central US) | org policy requires an `owner` tag |
| PostgreSQL Flexible Server | `artemis-pg-n1` | v16, `procurement` db, seeded 26/60/240/59 |
| Container Registry | `artemispocacrn1` | holds `dab:latest` (config baked in) |
| Container Apps env | `artemis-cae` | |
| DAB Container App | `artemis-dab` | auto REST+GraphQL+OpenAPI over the SoR |
| Entra app registration | `artemis-dab-easyauth` | single-tenant (AzureADMyOrg) |

**Region note:** `eastus`/`eastus2` are policy-restricted for these resources in this
subscription; **Central US** is used.

## Access (tenant-locked)

```
https://artemis-dab.icyocean-479340e8.centralus.azurecontainerapps.io/api/openapi
```

- **Before EasyAuth:** the endpoint returned data (HTTP 200) — verified the headline
  Artemis-3 row (`NSN-7209-452737`, risk 99) live in Azure.
- **After EasyAuth:** an unauthenticated request now gets **HTTP 401 / redirect to the
  Entra sign-in** — you must sign in with a **limitlessdata-tenant** account. This is the
  "must be in the tenant to use it" lock, identical in spirit to the DOT demo.

Open the URL in a browser while signed in to the tenant to reach the Swagger/OpenAPI and
the REST entities (`/api/Material`, `/api/SupplyRisk`, …).

## How this maps to the local POC

This is the **DAB + identity** slice of the local stack, deployed managed: Container Apps
hosts DAB; Entra (not the local RS256 issuer) provides the tenant auth. The full
gateway/catalog/registry layer maps to **Azure API Management / API Center** (see
`AZURE-DEPLOYMENT.md` and the Bicep under `infra/azure/`). Production hardening (private
networking so the SoR has no public path, APIM in front, managed identity to ACR) is the
documented next step.

## Teardown (stop billing)

```bash
az group delete -n artemis-poc-rg --yes --no-wait
az ad app delete --id <artemis-dab-easyauth appId>
```
