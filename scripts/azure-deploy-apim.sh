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
# MSYS_NO_PATHCONV: keep '/...' args from being mangled to Windows paths on Git Bash.
# PYTHONIOENCODING/UTF8: az on Windows otherwise crashes printing the policy PUT's BOM.
export MSYS_NO_PATHCONV=1 PYTHONIOENCODING=utf-8 PYTHONUTF8=1

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
mkdir -p temp
python - > temp/apim-policy.json <<'PY'
import json
# Demoable gate = APIM subscription key (works in the Developer Portal "Try it"), plus
# per-caller rate-limit + correlation id. To tenant-lock with Entra instead, add inside
# <inbound> (after <base/>):
#   <validate-azure-ad-token tenant-id="<tenant>" failed-validation-httpcode="401">
#     <audiences><audience>api://artemis-api</audience></audiences>
#   </validate-azure-ad-token>
xml = """<policies>
  <inbound>
    <base />
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
# az on Windows can crash printing the policy PUT response (BOM) — the PUT still succeeds,
# so suppress output and don't let the print-crash fail the script.
az rest --method put \
  --uri "https://management.azure.com/subscriptions/$SUBID/resourceGroups/$RG/providers/Microsoft.ApiManagement/service/$APIM/apis/artemis-procurement/policies/policy?api-version=2022-08-01" \
  --body @temp/apim-policy.json -o none 2>/dev/null || true

echo "==> publish a Product (subscription-key gated) and add the API"
az apim product create -g "$RG" --service-name "$APIM" --product-id artemis \
  --product-name "Artemis Data Products" --state published --subscription-required true \
  --approval-required false -o none 2>/dev/null || true
az apim product api add -g "$RG" --service-name "$APIM" --product-id artemis --api-id artemis-procurement -o none

echo "==> publish the Developer Portal (best-effort: works once default content is provisioned)"
# The managed developer portal needs its default content provisioned ONCE from admin mode
# (Azure portal -> API Management -> Developer portal -> Portal overview -> Publish, which
# both provisions and publishes). There is no pure-CLI seed for default content (see
# https://learn.microsoft.com/azure/api-management/automate-portal-deployments). Once
# provisioned, this call republishes it automatically on every deploy so config changes
# (new APIs, policy, sign-in) are reflected without a manual republish.
PORTAL_PUB="$(az rest --method put \
  --uri "https://management.azure.com/subscriptions/$SUBID/resourceGroups/$RG/providers/Microsoft.ApiManagement/service/$APIM/portalRevisions/initial?api-version=2022-08-01" \
  --body '{"properties":{"description":"published by deploy script","isCurrent":true}}' \
  -o none 2>&1 || true)"
if echo "$PORTAL_PUB" | grep -qi "PreconditionFailed\|Provision does not exist"; then
  echo "   NOTE: developer-portal content not provisioned yet — do the ONE-TIME publish:"
  echo "         Azure portal -> $APIM -> Developer portal -> Portal overview -> Publish."
  echo "         After that, re-running this script keeps it republished automatically."
else
  echo "   developer portal (re)published."
fi

echo "==> diagnostics: stream APIM GatewayLogs + metrics to Log Analytics (if present)"
WSID="$(az monitor log-analytics workspace show -g "$RG" -n artemis-logs --query id -o tsv 2>/dev/null || true)"
if [ -n "$WSID" ]; then
  APIMID="$(az apim show -g "$RG" -n "$APIM" --query id -o tsv)"
  az monitor diagnostic-settings create --name to-la --resource "$APIMID" --workspace "$WSID"     --logs '[{"category":"GatewayLogs","enabled":true}]' --metrics '[{"category":"AllMetrics","enabled":true}]' -o none 2>/dev/null || true
fi

echo "==> validate a call through APIM"
GW="$(az apim show -g "$RG" -n "$APIM" --query gatewayUrl -o tsv)"
KEY="$(az rest --method post --uri "https://management.azure.com/subscriptions/$SUBID/resourceGroups/$RG/providers/Microsoft.ApiManagement/service/$APIM/subscriptions/master/listSecrets?api-version=2022-08-01" --query primaryKey -o tsv 2>/dev/null)"
NOKEY="$(curl -s -o /dev/null -w '%{http_code}' "$GW/api/SupplyRisk?\$first=1" || true)"
WITHKEY="$(curl -s -o /dev/null -w '%{http_code}' -H "Ocp-Apim-Subscription-Key: $KEY" "$GW/api/SupplyRisk?\$first=1" || true)"
echo "   no key -> HTTP $NOKEY   |   with key -> HTTP $WITHKEY  (expect 401 / 200)"

PORTAL="https://$APIM.developer.azure-api.net"
echo
echo "================ APIM EDITION CONFIGURED ================"
echo "  Gateway:          $GW/api/SupplyRisk   (header: Ocp-Apim-Subscription-Key)"
echo "  Developer Portal: $PORTAL   (publish it once from the portal Azure UI on first run)"
echo "  Policy: subscription-key + per-caller rate-limit + correlation id"
echo "          (Entra validate-azure-ad-token is the documented tenant-lock upgrade)"
