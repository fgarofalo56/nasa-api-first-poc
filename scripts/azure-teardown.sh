#!/usr/bin/env bash
# Stop all Azure spend for this POC: delete the resource group (Postgres, ACR, Container
# Apps env + all apps, Log Analytics) and the Entra app registrations created for EasyAuth.
#
#   az login --tenant <tenant>
#   ./scripts/azure-teardown.sh            # prompts before deleting
#   ./scripts/azure-teardown.sh --yes      # no prompt
set -euo pipefail

RG="${RG:-artemis-poc-rg}"
SUB="${AZ_SUB:-FedCiv ATU FFL - Main}"
CONFIRM="${1:-}"

az account set --subscription "$SUB"

echo "This will DELETE resource group '$RG' (all resources) and the EasyAuth app registrations."
if [ "$CONFIRM" != "--yes" ]; then
  read -r -p "Type the resource group name to confirm: " ans
  [ "$ans" = "$RG" ] || { echo "aborted."; exit 1; }
fi

# Delete EasyAuth app registrations (front end + DAB) by display name.
for app in artemis-ui-easyauth artemis-dab-easyauth; do
  id="$(az ad app list --display-name "$app" --query '[0].appId' -o tsv 2>/dev/null || true)"
  if [ -n "$id" ]; then
    az ad app delete --id "$id" && echo "deleted app registration $app ($id)"
  fi
done

echo "Deleting resource group '$RG' (async)..."
az group delete -n "$RG" --yes --no-wait

# Key Vault soft-delete would block a same-name redeploy — purge it so the name frees up.
KV="${KV:-artemis-kv-n1}"
if az keyvault list-deleted --query "[?name=='$KV']" -o tsv 2>/dev/null | grep -q "$KV"; then
  az keyvault purge -n "$KV" 2>/dev/null && echo "purged soft-deleted Key Vault $KV" || true
fi

echo "Done. Resources are being deleted; billing stops as they are removed."
echo "Note: the Databricks notebook artifacts live in your dbw-btfabric-dev workspace —"
echo "drop them with: DROP SCHEMA dbw_btfabric_dev.bronze CASCADE; (silver/gold too)."
