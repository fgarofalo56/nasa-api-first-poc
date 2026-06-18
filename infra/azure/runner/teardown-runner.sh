#!/usr/bin/env bash
# Remove the self-hosted runner cleanly: deregister from GitHub, then delete the RG.
# Usage: SUBSCRIPTION="<sub>" ./infra/azure/runner/teardown-runner.sh
set -euo pipefail
REPO="${REPO:-fgarofalo56/nasa-api-first-poc}"
RG="${RG:-rg-ghrunner-nasa-poc}"
VM_NAME="${VM_NAME:-gh-runner-nasa-poc}"
[ -n "${SUBSCRIPTION:-}" ] || { echo "ERROR: set SUBSCRIPTION"; exit 2; }
az account set --subscription "$SUBSCRIPTION"

echo "==> Deregister the runner from GitHub (best effort)"
TOKEN="$(gh api -X POST "repos/$REPO/actions/runners/remove-token" --jq .token 2>/dev/null || true)"
if [ -n "$TOKEN" ]; then
  az vm run-command invoke -g "$RG" -n "$VM_NAME" --command-id RunShellScript --scripts "
    cd /home/runner/actions-runner 2>/dev/null || exit 0
    ./svc.sh stop || true; ./svc.sh uninstall || true
    sudo -u runner ./config.sh remove --token '$TOKEN' || true
  " --query "value[0].message" -o tsv 2>/dev/null || true
fi
# Also drop any stale runner registration via the API by id.
for id in $(gh api "repos/$REPO/actions/runners" --jq '.runners[] | select(.name=="'"$VM_NAME"'") | .id' 2>/dev/null); do
  gh api -X DELETE "repos/$REPO/actions/runners/$id" 2>/dev/null || true
done

echo "==> Delete resource group $RG"
az group delete -n "$RG" --yes --no-wait
echo "done (RG deletion running in background)."
