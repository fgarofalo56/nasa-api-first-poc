#!/usr/bin/env bash
# Deploy + register a self-hosted GitHub Actions runner on a small Azure Linux VM.
#
# Why: GitHub-hosted runners are billing-blocked on this account, so CI runs on our own
# Azure compute instead. The VM has NO public IP and NO inbound ports — the runner only
# makes OUTBOUND calls to GitHub, and we manage it through `az vm run-command` (control
# plane), so there's nothing to attack from the internet. The repo is private, so a
# self-hosted runner is safe (no untrusted fork PRs execute on it).
#
# Prereqs (run by YOU — interactive):
#   az login --tenant <limitlessdata-tenant>      # the subscription that should bear the cost
#   gh auth status                                 # needs repo admin to mint a runner token
#
# Usage:
#   SUBSCRIPTION="<limitlessdata-sub-id-or-name>" ./infra/azure/runner/deploy-runner.sh
# Optional overrides: RG, LOCATION, VM_NAME, VM_SIZE, REPO, ADMIN_USER, LABELS
set -euo pipefail

REPO="${REPO:-fgarofalo56/nasa-api-first-poc}"
RG="${RG:-rg-ghrunner-nasa-poc}"
LOCATION="${LOCATION:-eastus2}"
VM_NAME="${VM_NAME:-gh-runner-nasa-poc}"
VM_SIZE="${VM_SIZE:-Standard_B2s}"          # 2 vCPU / 4 GB — adequate for ruff+pytest+node+small compose
ADMIN_USER="${ADMIN_USER:-azureuser}"
LABELS="${LABELS:-self-hosted,linux,x64,azure,nasa-poc}"
IMAGE="${IMAGE:-Ubuntu2204}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[ -n "${SUBSCRIPTION:-}" ] || { echo "ERROR: set SUBSCRIPTION to the limitlessdata subscription"; exit 2; }
command -v az >/dev/null || { echo "ERROR: az CLI not found"; exit 2; }
command -v gh >/dev/null || { echo "ERROR: gh CLI not found"; exit 2; }

echo "==> Subscription"
az account set --subscription "$SUBSCRIPTION"
az account show --query "{name:name, id:id}" -o tsv

echo "==> Resource group $RG ($LOCATION)"
az group create -n "$RG" -l "$LOCATION" -o none

echo "==> VM $VM_NAME ($VM_SIZE) — no public IP, no inbound"
az vm create -g "$RG" -n "$VM_NAME" \
  --image "$IMAGE" --size "$VM_SIZE" \
  --admin-username "$ADMIN_USER" --generate-ssh-keys \
  --public-ip-address "" --nsg-rule NONE \
  --custom-data "$HERE/cloud-init.yaml" \
  --tags project=nasa-api-first-poc purpose=github-actions-runner -o none
echo "    VM created. Waiting for cloud-init (docker + runner download)…"

# Poll for the cloud-init completion marker via run-command (no SSH needed).
for i in $(seq 1 40); do
  done_marker="$(az vm run-command invoke -g "$RG" -n "$VM_NAME" --command-id RunShellScript \
    --scripts "test -f /home/runner/.cloud-init-done && echo READY || echo WAIT" \
    --query "value[0].message" -o tsv 2>/dev/null | grep -o READY || true)"
  [ "$done_marker" = "READY" ] && { echo "    cloud-init done"; break; }
  echo "    ($i/40) still bootstrapping…"; sleep 15
done

echo "==> Minting a runner registration token (short-lived)"
TOKEN="$(gh api -X POST "repos/$REPO/actions/runners/registration-token" --jq .token)"
[ -n "$TOKEN" ] || { echo "ERROR: failed to mint registration token"; exit 1; }

echo "==> Registering + starting the runner as a service"
az vm run-command invoke -g "$RG" -n "$VM_NAME" --command-id RunShellScript --scripts "
set -e
cd /home/runner/actions-runner
sudo -u runner ./config.sh --unattended --replace \
  --url 'https://github.com/$REPO' --token '$TOKEN' \
  --name '$VM_NAME' --labels '$LABELS' --work _work
./svc.sh install runner
./svc.sh start
./svc.sh status | head -5
" --query "value[0].message" -o tsv

echo "==> Verifying the runner is online in GitHub"
sleep 8
gh api "repos/$REPO/actions/runners" --jq '.runners[] | {name, status, labels: [.labels[].name]}'

cat <<EOF

✅ Runner deployed. Next: point CI at it by changing 'runs-on: ubuntu-latest' to
   'runs-on: [self-hosted, linux, x64]' in .github/workflows/ci.yml (and others you want
   self-hosted). See infra/azure/runner/README.md.

Cost note: $VM_SIZE runs ~24x7. To pause billing when idle:
   az vm deallocate -g $RG -n $VM_NAME      # stop (no compute charge; CI offline)
   az vm start      -g $RG -n $VM_NAME      # resume
Or attach an auto-shutdown schedule (see README).
EOF
