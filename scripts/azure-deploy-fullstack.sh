#!/usr/bin/env bash
# Deploy the FULL stack to Azure Container Apps: NASA UI + Kong gateway + identity +
# catalog + registry + transportation + DAB, with both sources pre-registered and the
# front end tenant-locked with Entra EasyAuth.
#
# Pragmatic ACA port of the compose topology:
#   * all apps use external ingress + public FQDNs (no internal-DNS chicken-and-egg);
#   * the gateway config is baked with a fixed demo RSA keypair (issuer gets the private
#     key as a secret) so there is no shared volume;
#   * both sources (Artemis + DOT transportation) are pre-registered in kong.yml
#     (the live "add a source" wizard needs Kong's admin port and stays a local feature);
#   * Prometheus/Grafana are not deployed here (Kong's metrics port isn't exposed in ACA;
#     use Azure Monitor or local `make obs`).
#
# Prereqs: az login (tenant), PG_ADMIN_PASSWORD set, the per-service images built in ACR
# (see the loop near the top). Run from the repo root.
set -euo pipefail
cd "$(dirname "$0")/.."

RG="${RG:-artemis-poc-rg}"; LOC="${LOC:-centralus}"
ACR="${ACR:-artemispocacrn1}"; CAE="${CAE:-artemis-cae}"
PG_FQDN="${PG_FQDN:-artemis-pg-n1.postgres.database.azure.com}"
: "${PG_ADMIN_PASSWORD:?set PG_ADMIN_PASSWORD}"
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1 MSYS_NO_PATHCONV=1
TENANT="$(az account show --query tenantId -o tsv)"
ACRSRV="$ACR.azurecr.io"
AU="$(az acr credential show -n "$ACR" --query username -o tsv)"
AP="$(az acr credential show -n "$ACR" --query 'passwords[0].value' -o tsv)"
TAGS=(owner=fgarofalo@limitlessdata.ai project=nasa-api-first-poc)
mkdir -p temp/deploy

echo "==> 0. demo RSA keypair (baked into the gateway config; private key -> issuer secret)"
python - <<'PY'
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
open("temp/deploy/jwt-private.pem","wb").write(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
open("temp/deploy/jwt-public.pem","wb").write(k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
print("keypair written")
PY
PRIV_B64="$(base64 -w0 temp/deploy/jwt-private.pem 2>/dev/null || base64 temp/deploy/jwt-private.pem | tr -d '\n')"

echo "==> 1. (re)build images that changed (identity: key env; catalog: SOURCES_JSON env)"
for svc in identity catalog transportation registry; do
  az acr build -r "$ACR" -t "$svc:latest" -f "services/$svc/Dockerfile" . --no-logs >/dev/null
done

deploy() {  # name image port [extra args...]
  local name="$1" img="$2" port="$3"; shift 3
  if az containerapp show -g "$RG" -n "$name" >/dev/null 2>&1; then
    az containerapp update -g "$RG" -n "$name" --image "$ACRSRV/$img" "$@" -o none
  else
    az containerapp create -g "$RG" -n "$name" --environment "$CAE" --image "$ACRSRV/$img" \
      --registry-server "$ACRSRV" --registry-username "$AU" --registry-password "$AP" \
      --target-port "$port" --ingress external --min-replicas 1 --max-replicas 2 \
      --cpu 0.5 --memory 1.0Gi --tags "${TAGS[@]}" "$@" -o none
  fi
  az containerapp show -g "$RG" -n "$name" --query properties.configuration.ingress.fqdn -o tsv
}

echo "==> 1b. observability: Log Analytics workspace + stream env app logs to it"
az monitor log-analytics workspace create -g "$RG" -n artemis-logs -l "$LOC" \
  --tags "${TAGS[@]}" -o none 2>/dev/null || true
LA_CID="$(az monitor log-analytics workspace show -g "$RG" -n artemis-logs --query customerId -o tsv)"
LA_KEY="$(az monitor log-analytics workspace get-shared-keys -g "$RG" -n artemis-logs --query primarySharedKey -o tsv)"
az containerapp env update -g "$RG" -n "$CAE" --logs-destination log-analytics \
  --logs-workspace-id "$LA_CID" --logs-workspace-key "$LA_KEY" -o none 2>/dev/null || true

echo "==> 1c. enable Microsoft Sentinel (SIEM) on the workspace — idempotent"
SUBID="${SUBID:-$(az account show --query id -o tsv)}"
az rest --method put \
  --uri "https://management.azure.com/subscriptions/$SUBID/resourceGroups/$RG/providers/Microsoft.OperationalInsights/workspaces/artemis-logs/providers/Microsoft.SecurityInsights/onboardingStates/default?api-version=2024-03-01" \
  --body '{"properties":{}}' -o none 2>/dev/null || true

echo "==> 2. DAB: rebuild image (carries dab-config.json incl. column permissions) + drop EasyAuth"
# Use a content-derived tag so a dab-config.json change (e.g. field-level redaction)
# always produces a NEW revision — ACA will not re-pull an unchanged :latest tag.
DAB_TAG="dab:$(git rev-parse --short HEAD 2>/dev/null || echo manual)"
az acr build -r "$ACR" -t "$DAB_TAG" -f services/dab/Dockerfile services/dab --no-logs >/dev/null
az containerapp update -g "$RG" -n artemis-dab --image "$ACRSRV/$DAB_TAG" -o none 2>/dev/null || true
az containerapp auth update -g "$RG" -n artemis-dab --action AllowAnonymous -o none 2>/dev/null || true
DAB_FQDN="$(az containerapp show -g "$RG" -n artemis-dab --query properties.configuration.ingress.fqdn -o tsv)"

echo "==> 2b. Key Vault: store the DB connection string + back the DAB secret with it (managed identity)"
# Production-hardening: the DAB connection string lives in Key Vault, and the DAB app
# reads it at runtime via its system-assigned managed identity + a Key Vault reference —
# so the secret value is never inlined in the app's config. Idempotent.
KV="${KV:-artemis-kv-n1}"
SUBID="$(az account show --query id -o tsv)"
az keyvault show -n "$KV" -g "$RG" >/dev/null 2>&1 || \
  az keyvault create -n "$KV" -g "$RG" -l "$LOC" --enable-rbac-authorization true --tags "${TAGS[@]}" -o none
KVID="/subscriptions/$SUBID/resourceGroups/$RG/providers/Microsoft.KeyVault/vaults/$KV"
ME="$(az ad signed-in-user show --query id -o tsv)"
az role assignment create --assignee-object-id "$ME" --assignee-principal-type User \
  --role "Key Vault Secrets Officer" --scope "$KVID" -o none 2>/dev/null || true
sleep 20  # RBAC propagation before the data-plane secret write
DAB_CONN="Host=$PG_FQDN;Port=5432;Database=procurement;Username=artemis;Password=$PG_ADMIN_PASSWORD;SSL Mode=Require;Trust Server Certificate=true"
az keyvault secret set --vault-name "$KV" --name dab-conn --value "$DAB_CONN" -o none
# give the DAB app a managed identity + read access, then point its secret at the vault
DAB_PID="$(az containerapp identity assign -g "$RG" -n artemis-dab --system-assigned -o none 2>/dev/null; \
           az containerapp show -g "$RG" -n artemis-dab --query identity.principalId -o tsv)"
az role assignment create --assignee-object-id "$DAB_PID" --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" --scope "$KVID" -o none 2>/dev/null || true
sleep 60  # RBAC propagation before the app resolves the reference
az containerapp secret set -g "$RG" -n artemis-dab \
  --secrets "dab-conn=keyvaultref:https://$KV.vault.azure.net/secrets/dab-conn,identityref:system" -o none
# ensure the DAB env var consumes the (now KV-backed) secret, then restart to pick it up
az containerapp update -g "$RG" -n artemis-dab \
  --set-env-vars "DAB_CONNECTION_STRING=secretref:dab-conn" -o none 2>/dev/null || true

echo "==> 3. backends: transportation, identity, catalog, registry"
TRANSPORT_FQDN="$(deploy transportation transportation:latest 8200 \
  --env-vars TRANSPORT_PORT=8200)"
IDENT_FQDN="$(deploy identity identity:latest 8081 \
  --secrets "jwtkey=$PRIV_B64" \
  --env-vars ISSUER_PORT=8081 JWT_ISSUER=https://issuer.local JWT_AUDIENCE=artemis-api \
             KONG_TEMPLATE=/nonexistent JWT_PRIVATE_KEY_PEM=secretref:jwtkey)"

DOT_SOURCES_JSON="[{\"id\":\"dot-bridges\",\"title\":\"DOT Transportation - Bridge Inventory\",\"base_path\":\"/dot\",\"owner\":\"US DOT (synthetic)\",\"domain\":\"Transportation / Infrastructure\",\"classification_label\":\"Routine\",\"sample_path\":\"/dot/api/Bridge?\$orderby=condition_rating asc&\$first=8\",\"require_jwt\":true}]"

echo "==> 4. render + build the gateway image (both sources, ACA FQDNs, demo pubkey)"
PUB_PEM="$(cat temp/deploy/jwt-public.pem)" DABF="$DAB_FQDN" TRF="$TRANSPORT_FQDN" \
python - <<'PY'
import os, yaml
pub = os.environ["PUB_PEM"]
dab = f"https://{os.environ['DABF']}"
tr  = f"https://{os.environ['TRF']}"
jwt = {"name":"jwt","config":{"key_claim_name":"client_id","run_on_preflight":False,"claims_to_verify":["exp"]}}
rl  = {"name":"rate-limiting","config":{"minute":60,"policy":"local","limit_by":"consumer","fault_tolerant":True}}
cors= {"name":"cors","config":{"origins":["*"],"methods":["GET","OPTIONS"],"headers":["Authorization","Content-Type"],"exposed_headers":["X-Correlation-ID"],"credentials":False,"preflight_continue":False}}
corr= {"name":"correlation-id","config":{"header_name":"X-Correlation-ID","generator":"uuid#counter","echo_downstream":True}}
cfg = {"_format_version":"3.0","_transform":True,
  "services":[
    {"name":"artemis-dab","url":dab,"routes":[
        {"name":"artemis-openapi","paths":["/api/openapi"],"strip_path":False},
        {"name":"artemis-api","paths":["/api/Material","/api/Vendor","/api/PurchaseOrder","/api/SupplyRisk","/graphql"],"strip_path":False,"plugins":[jwt,rl,cors]}],
     "plugins":[corr]},
    {"name":"src-dot","url":tr,"routes":[
        {"name":"route-dot","paths":["/dot"],"strip_path":True,"plugins":[jwt,rl,cors]}],
     "plugins":[corr]},
  ],
  "consumers":[
    {"username":"analyst","jwt_secrets":[{"key":"analyst","algorithm":"RS256","rsa_public_key":pub}]},
    {"username":"artemis-agent","jwt_secrets":[{"key":"artemis-agent","algorithm":"RS256","rsa_public_key":pub}]},
  ]}
import pathlib; d=pathlib.Path("temp/deploy/kong-build"); d.mkdir(parents=True,exist_ok=True)
(d/"kong.yml").write_text(yaml.safe_dump(cfg,sort_keys=False),encoding="utf-8")
(d/"Dockerfile").write_text("FROM kong:3.8\nCOPY kong.yml /kong.yml\n",encoding="utf-8")
print("kong build context ready")
PY
az acr build -r "$ACR" -t kong:latest -f temp/deploy/kong-build/Dockerfile temp/deploy/kong-build --no-logs >/dev/null
KONG_FQDN="$(deploy kong kong:latest 8000 \
  --env-vars KONG_DATABASE=off KONG_DECLARATIVE_CONFIG=/kong.yml KONG_PROXY_LISTEN=0.0.0.0:8000 \
             KONG_ADMIN_LISTEN=0.0.0.0:8001 KONG_PLUGINS=bundled)"

echo "==> 5. registry (DOT pre-seeded + removable) + catalog (reads the registry live)"
# Registry is the source of truth for add/remove. Seed DOT so it's present-by-default yet
# removable (and re-addable via the wizard); the /dot Kong route is pre-baked above, so a
# re-added DOT routes immediately even though ACA can't hot-reload Kong's admin.
SEED_DOT="[{\"id\":\"dot-bridges\",\"title\":\"DOT Transportation - Bridge Inventory\",\"upstream_url\":\"https://$TRANSPORT_FQDN\",\"base_path\":\"/dot\",\"owner\":\"US DOT (synthetic)\",\"domain\":\"Transportation / Infrastructure\",\"classification_label\":\"Routine\",\"require_jwt\":true,\"sample_path\":\"/dot/api/Bridge?\$orderby=condition_rating asc&\$first=8\"}]"
REG_FQDN="$(deploy registry registry:latest 8095 \
  --env-vars REGISTRY_PORT=8095 "KONG_ADMIN_INTERNAL_URL=https://$KONG_FQDN" "SEED_SOURCES_JSON=$SEED_DOT")"
# Pin the registry to ONE replica: its source list is in-memory/ephemeral per replica, so
# multiple replicas would diverge (a remove on one wouldn't be seen by the catalog's read).
az containerapp update -g "$RG" -n registry --min-replicas 1 --max-replicas 1 -o none 2>/dev/null || true
CAT_FQDN="$(deploy catalog catalog:latest 8080 \
  --env-vars "KONG_PUBLIC_URL=https://$KONG_FQDN" "REGISTRY_INTERNAL_URL=https://$REG_FQDN")"

echo "==> 5b. MCP server (agent path) — reaches the gateway/issuer over their Azure URLs"
az acr build -r "$ACR" -t mcp:latest -f services/mcp/Dockerfile . --no-logs >/dev/null
MCP_FQDN="$(deploy mcp mcp:latest 8090 --min-replicas 1 \
  --env-vars MCP_PORT=8090 "KONG_INTERNAL_URL=https://$KONG_FQDN" "IDENTITY_INTERNAL_URL=https://$IDENT_FQDN" JWT_AUDIENCE=artemis-api)"

echo "==> 5c. mission agent (grounded chat: NL -> MCP tools -> gateway -> cited answer)"
az acr build -r "$ACR" -t agent:latest -f services/agent/Dockerfile . --no-logs >/dev/null
AGENT_FQDN="$(deploy agent agent:latest 8110 --min-replicas 1 \
  --env-vars AGENT_PORT=8110 "MCP_URL=https://$MCP_FQDN/mcp")"

echo "==> 6. render UI config + build the frontend image (points at the Azure URLs)"
cat > frontend/public/config.js <<EOF
window.APP_CONFIG = {
  kong: "https://$KONG_FQDN",
  identity: "https://$IDENT_FQDN",
  catalog: "https://$CAT_FQDN",
  registry: "https://$REG_FQDN",
  agent: "https://$AGENT_FQDN",
  // Live add/remove works in Azure via the registry (the catalog reads it live); DOT is
  // pre-seeded + removable, and re-adds route through the pre-baked /dot Kong route.
  liveOnboarding: true,
  authEnabled: true,
};
EOF
az acr build -r "$ACR" -t frontend:latest -f frontend/Dockerfile . --no-logs >/dev/null
git checkout -- frontend/public/config.js   # restore the local default
FE_FQDN="$(deploy frontend frontend:latest 80)"

echo "==> 7. tenant-lock the front end with Entra EasyAuth (single-tenant)"
# --enable-id-token-issuance is REQUIRED: ACA EasyAuth uses the hybrid flow
# (response_type=code id_token, form_post), so without ID-token issuance the user signs in
# successfully and then gets HTTP 401 from the app. (Found in browser E2E.)
APPID="$(az ad app create --display-name artemis-ui-easyauth --sign-in-audience AzureADMyOrg \
  --enable-id-token-issuance true \
  --web-redirect-uris "https://$FE_FQDN/.auth/login/aad/callback" --query appId -o tsv)"
SECRET="$(az ad app credential reset --id "$APPID" --append --display-name easyauth --query password -o tsv)"
az containerapp auth microsoft update -g "$RG" -n frontend --client-id "$APPID" --client-secret "$SECRET" --tenant-id "$TENANT" --yes -o none
# AllowAnonymous (not RedirectToLoginPage): the SPA shows a PUBLIC landing page with a
# "Sign in with Microsoft" button (deferred auth, DOT-style) — so don't auto-redirect.
az containerapp auth update -g "$RG" -n frontend --action AllowAnonymous --redirect-provider azureactivedirectory --enabled true -o none

echo
echo "================ FULL STACK DEPLOYED ================"
echo "  NASA UI (tenant-locked):  https://$FE_FQDN"
echo "  Gateway:   https://$KONG_FQDN     Identity: https://$IDENT_FQDN"
echo "  Catalog:   https://$CAT_FQDN     Registry: https://$REG_FQDN"
echo "  DAB:       https://$DAB_FQDN     Transport: https://$TRANSPORT_FQDN"
echo "  MCP:       https://$MCP_FQDN     (agent path)"
echo "  Agent:     https://$AGENT_FQDN     (grounded chat over MCP)"
echo "Teardown: az group delete -n $RG --yes --no-wait  (+ az ad app delete --id $APPID)"
