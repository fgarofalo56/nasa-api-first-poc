#!/usr/bin/env bash
# Deploy the auto-API over a managed system of record to Azure, tenant-locked with
# Entra EasyAuth (the "DOT example" pattern). Functional demo variant: PostgreSQL
# Flexible Server + Data API Builder on Container Apps + Microsoft Entra built-in auth.
#
# Prereqs: az login (into the target tenant), and PG_ADMIN_PASSWORD set in the env.
# Nothing here is committed as a secret — the password comes from the environment.
#
#   az login --tenant <tenant-id>
#   export PG_ADMIN_PASSWORD='<strong-password>'
#   ./scripts/azure-deploy.sh
set -euo pipefail

SUB="${AZ_SUB:-FedCiv ATU FFL - Main}"
RG="${RG:-artemis-poc-rg}"
LOC="${LOC:-centralus}"            # eastus/eastus2 were policy-restricted in this sub
PG="${PG:-artemis-pg-n1}"
ACR="${ACR:-artemispocacrn1}"
CAE="${CAE:-artemis-cae}"
DABAPP="${DABAPP:-artemis-dab}"
TAGS=(owner="${OWNER_TAG:-$(az account show --query user.name -o tsv)}" project=nasa-api-first-poc)
: "${PG_ADMIN_PASSWORD:?set PG_ADMIN_PASSWORD in the environment}"

az account set --subscription "$SUB"

echo "==> resource group (org policy requires an 'owner' tag)"
az group create -n "$RG" -l "$LOC" --tags "${TAGS[@]}" -o none

echo "==> PostgreSQL Flexible Server + database"
MYIP="$(curl -s https://api.ipify.org)"
az postgres flexible-server create -g "$RG" -n "$PG" -l "$LOC" \
  --tier Burstable --sku-name Standard_B1ms --storage-size 32 --version 16 \
  --admin-user artemis --admin-password "$PG_ADMIN_PASSWORD" \
  --public-access "$MYIP" --yes --tags "${TAGS[@]}" -o none
az postgres flexible-server db create -g "$RG" -s "$PG" -d procurement -o none
az postgres flexible-server firewall-rule create -g "$RG" -n "$PG" \
  --rule-name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0 -o none
PGFQDN="$(az postgres flexible-server show -g "$RG" -n "$PG" --query fullyQualifiedDomainName -o tsv)"

echo "==> seed the cloud Postgres (run the seeder image on a network with egress)"
docker build -t nasa-seeder -f services/seeder/Dockerfile . >/dev/null
docker run --rm \
  -e POSTGRES_HOST="$PGFQDN" -e POSTGRES_DB=procurement \
  -e POSTGRES_USER=artemis -e POSTGRES_PASSWORD="$PG_ADMIN_PASSWORD" nasa-seeder

echo "==> ACR + cloud-build the DAB image (bakes dab-config.json)"
az acr create -g "$RG" -n "$ACR" --sku Basic --admin-enabled true --tags "${TAGS[@]}" -o none
az acr build -r "$ACR" -t dab:latest -f services/dab/Dockerfile services/dab

echo "==> Container Apps environment + DAB app over the cloud SoR"
az containerapp env create -g "$RG" -n "$CAE" -l "$LOC" --logs-destination none --tags "${TAGS[@]}" -o none
ACRUSER="$(az acr credential show -n "$ACR" --query username -o tsv)"
ACRPASS="$(az acr credential show -n "$ACR" --query 'passwords[0].value' -o tsv)"
CONN="Host=$PGFQDN;Port=5432;Database=procurement;Username=artemis;Password=$PG_ADMIN_PASSWORD;SSL Mode=Require;Trust Server Certificate=true"
az containerapp create -g "$RG" -n "$DABAPP" --environment "$CAE" \
  --image "$ACR.azurecr.io/dab:latest" \
  --registry-server "$ACR.azurecr.io" --registry-username "$ACRUSER" --registry-password "$ACRPASS" \
  --target-port 5000 --ingress external \
  --secrets "dab-conn=$CONN" \
  --env-vars "DAB_CONNECTION_STRING=secretref:dab-conn" "ASPNETCORE_URLS=http://0.0.0.0:5000" \
  --min-replicas 1 --max-replicas 2 --cpu 0.5 --memory 1.0Gi --tags "${TAGS[@]}" -o none
DABFQDN="$(az containerapp show -g "$RG" -n "$DABAPP" --query properties.configuration.ingress.fqdn -o tsv)"

echo "==> Entra EasyAuth (single-tenant — must be in the tenant to use it)"
TENANT="$(az account show --query tenantId -o tsv)"
APPID="$(az ad app create --display-name artemis-dab-easyauth --sign-in-audience AzureADMyOrg \
  --web-redirect-uris "https://$DABFQDN/.auth/login/aad/callback" --query appId -o tsv)"
SECRET="$(az ad app credential reset --id "$APPID" --append --display-name easyauth --query password -o tsv)"
az containerapp auth microsoft update -g "$RG" -n "$DABAPP" \
  --client-id "$APPID" --client-secret "$SECRET" --tenant-id "$TENANT" --yes -o none
az containerapp auth update -g "$RG" -n "$DABAPP" \
  --action RedirectToLoginPage --redirect-provider azureactivedirectory --enabled true -o none

echo
echo "Deployed. Tenant-locked auto-API:"
echo "  https://$DABFQDN/api/openapi   (sign in with a $TENANT account)"
echo "Teardown: az group delete -n $RG --yes --no-wait  (+ az ad app delete --id $APPID)"
