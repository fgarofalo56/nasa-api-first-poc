#!/usr/bin/env bash
# APIM edition — configure Azure API Management as the managed gateway in front of the
# deployed DAB auto-API: import the API from its OpenAPI, apply the policy that mirrors
# the Kong plugins (Entra JWT validation + rate-limit + correlation id), publish a
# Product, and surface the Developer Portal.
#
# Prereq: the APIM instance is already provisioning/provisioned (Developer tier has the
# Developer Portal). Start it with:
#   az apim create -g artemis-poc-rg -n artemis-apim-n1 -l centralus \
#     --publisher-email you@org --publisher-name "..." --sku-name Developer
set -euo pipefail
export MSYS_NO_PATHCONV=1

RG="${RG:-artemis-poc-rg}"; APIM="${APIM:-artemis-apim-n1}"
DOMAIN="${ACA_DOMAIN:-icyocean-479340e8.centralus.azurecontainerapps.io}"
DAB="https://artemis-dab.$DOMAIN"
SUBID="$(az account show --query id -o tsv)"
TENANT="$(az account show --query tenantId -o tsv)"

echo "==> wait for APIM to finish provisioning (Developer tier ~30-45 min)"
until [ "$(az apim show -g "$RG" -n "$APIM" --query provisioningState -o tsv 2>/dev/null)" = "Succeeded" ]; do
  echo "   ...$(az apim show -g "$RG" -n "$APIM" --query provisioningState -o tsv 2>/dev/null)"; sleep 60
done

echo "==> import the DAB REST API from its OpenAPI"
az apim api import -g "$RG" --service-name "$APIM" \
  --path api --api-id artemis-procurement \
  --display-name "Artemis Supply-Chain Risk API" \
  --specification-format OpenApi --specification-url "$DAB/api/openapi" \
  --service-url "$DAB/api" --protocols https

echo "==> apply the gateway policy (mirrors the Kong plugins)"
python - "$TENANT" > temp/apim-policy.json <<'PY'
import json, sys
tenant = sys.argv[1]
xml = f"""<policies>
  <inbound>
    <base />
    <!-- Tenant-grade identity: validate an Entra token (managed equivalent of Kong jwt). -->
    <validate-azure-ad-token tenant-id="{tenant}" failed-validation-httpcode="401">
      <audiences><audience>api://artemis-api</audience></audiences>
    </validate-azure-ad-token>
    <!-- Per-caller quota (managed equivalent of Kong rate-limiting). -->
    <rate-limit-by-key calls="60" renewal-period="60"
      counter-key="@(context.Subscription?.Id ?? context.Request.IpAddress)" />
    <set-header name="X-Correlation-ID" exists-action="skip">
      <value>@(context.RequestId.ToString())</value>
    </set-header>
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
  <on-error><base /></on-error>
</policies>"""
print(json.dumps({"properties": {"format": "xml", "value": xml}}))
PY
az rest --method put \
  --uri "https://management.azure.com/subscriptions/$SUBID/resourceGroups/$RG/providers/Microsoft.ApiManagement/service/$APIM/apis/artemis-procurement/policies/policy?api-version=2022-08-01" \
  --body @temp/apim-policy.json -o none

echo "==> publish a Product and add the API"
az apim product create -g "$RG" --service-name "$APIM" --product-id artemis \
  --product-name "Artemis Data Products" --state published --subscription-required true \
  --approval-required false 2>/dev/null || true
az apim product api add -g "$RG" --service-name "$APIM" --product-id artemis --api-id artemis-procurement

GW="$(az apim show -g "$RG" -n "$APIM" --query gatewayUrl -o tsv)"
PORTAL="https://$APIM.developer.azure-api.net"
echo
echo "================ APIM EDITION CONFIGURED ================"
echo "  Gateway:          $GW/api/SupplyRisk"
echo "  Developer Portal: $PORTAL   (publish it once in the portal Azure UI if first run)"
echo "  Policy: Entra JWT validation + per-caller rate-limit + correlation id"
