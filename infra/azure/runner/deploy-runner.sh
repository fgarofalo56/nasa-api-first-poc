#!/usr/bin/env bash
# Deploy + register a self-hosted GitHub Actions runner on a small Azure Linux VM.
#
# Why: GitHub-hosted runner minutes are billing-blocked on this account, so CI runs on our
# own Azure compute instead. The VM has NO public IP and NO inbound ports — the runner only
# makes OUTBOUND calls to GitHub, and we manage it through `az vm run-command` (control
# plane), so there's nothing to attack from the internet. The repo is private, so a
# self-hosted runner is safe (no untrusted fork PRs execute on it).
#
# Tailored for the Limitless Data "FedCiv ATU FFL" landing zones, which have an EGRESS
# ALLOWLIST: GitHub, packages.microsoft.com, MCR, Docker Hub, and PyPI are reachable, but
# the Ubuntu apt mirror (azure.archive.ubuntu.com) is BLOCKED. So we do NOT use apt:
#   - Docker is installed from download.docker.com STATIC binaries (allowlisted).
#   - The runner's installdependencies.sh is skipped — its libs (libicu, libssl, zlib,
#     libkrb5) are already on the Ubuntu 22.04 image; liblttng-ust is optional.
#   - git + python3 are preinstalled (used by actions/checkout and version parsing).
# Provisioning runs via `az vm run-command` (NOT cloud-init custom-data) to avoid a Windows
# CRLF pitfall where a CRLF `#cloud-config` line is silently ignored.
#
# Prereqs (run by YOU — interactive):
#   az login [--use-device-code]                  # the limitlessdata account/sub to bill
#   gh auth status                                # needs repo admin to mint a runner token
#
# Usage:
#   SUBSCRIPTION="FedCiv ATU FFL - Main" ./infra/azure/runner/deploy-runner.sh
# Optional overrides: RG, LOCATION, VM_NAME, VM_SIZE, REPO, ADMIN_USER, LABELS
set -euo pipefail

REPO="${REPO:-fgarofalo56/nasa-api-first-poc}"
RG="${RG:-rg-ghrunner-nasa-poc}"
LOCATION="${LOCATION:-centralus}"           # B2s capacity proven here; same region as the POC stack
VM_NAME="${VM_NAME:-gh-runner-nasa-poc}"
VM_SIZE="${VM_SIZE:-Standard_B2s}"          # 2 vCPU / 4 GB — adequate for ruff+pytest+node+small compose
ADMIN_USER="${ADMIN_USER:-azureuser}"
LABELS="${LABELS:-self-hosted,linux,x64,azure,nasa-poc}"
IMAGE="${IMAGE:-Ubuntu2204}"
PROJECT_TAG="${PROJECT_TAG:-nasa-api-first-poc}"
OWNER_TAG="${OWNER_TAG:-$(az account show --query user.name -o tsv 2>/dev/null || echo unknown)}"

[ -n "${SUBSCRIPTION:-}" ] || { echo "ERROR: set SUBSCRIPTION"; exit 2; }
command -v az >/dev/null || { echo "ERROR: az CLI not found"; exit 2; }
command -v gh >/dev/null || { echo "ERROR: gh CLI not found"; exit 2; }

rc() {  # run a shell script on the VM via the control plane; print its combined output
  az vm run-command invoke -g "$RG" -n "$VM_NAME" --command-id RunShellScript \
    --scripts "$1" --query "value[0].message" -o tsv 2>&1
}

echo "==> Subscription"; az account set --subscription "$SUBSCRIPTION"
az account show --query "{name:name, id:id}" -o tsv

echo "==> Resource group $RG ($LOCATION)"
az group create -n "$RG" -l "$LOCATION" \
  --tags project="$PROJECT_TAG" owner="$OWNER_TAG" purpose=github-actions-runner -o none

echo "==> VM $VM_NAME ($VM_SIZE) — no public IP, no inbound"
az vm create -g "$RG" -n "$VM_NAME" \
  --image "$IMAGE" --size "$VM_SIZE" \
  --admin-username "$ADMIN_USER" --generate-ssh-keys \
  --public-ip-address "" --nsg-rule NONE \
  --tags project="$PROJECT_TAG" owner="$OWNER_TAG" purpose=github-actions-runner -o none
echo "    VM created."

echo "==> Provisioning (static Docker + runner, no apt) via run-command — a few minutes"
PROV=$(rc '
set -e
# Docker via STATIC binaries (Ubuntu apt mirror is blocked in this landing zone).
TGZ=$(curl -fsSL https://download.docker.com/linux/static/stable/x86_64/ | grep -oE "docker-[0-9]+\.[0-9]+\.[0-9]+\.tgz" | sort -V | tail -1)
curl -fsSL -o /tmp/docker.tgz "https://download.docker.com/linux/static/stable/x86_64/${TGZ}"
tar xzf /tmp/docker.tgz -C /tmp && install -m0755 /tmp/docker/* /usr/local/bin/ && rm -rf /tmp/docker /tmp/docker.tgz
cat >/etc/systemd/system/docker.service <<UNIT
[Unit]
Description=Docker Engine (static)
After=network-online.target
Wants=network-online.target
[Service]
ExecStart=/usr/local/bin/dockerd --host=unix:///var/run/docker.sock
Restart=always
Delegate=yes
KillMode=process
[Install]
WantedBy=multi-user.target
UNIT
getent group docker >/dev/null || groupadd docker
systemctl daemon-reload && systemctl enable --now docker
id runner >/dev/null 2>&1 || useradd -m -s /bin/bash runner
usermod -aG docker runner
# Runner binary (parse latest version without jq, which would need apt).
ver=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | python3 -c "import sys,json;print(json.load(sys.stdin)[\"tag_name\"].lstrip(\"v\"))")
install -d -o runner -g runner /home/runner/actions-runner
cd /home/runner/actions-runner
curl -fsSL -o runner.tar.gz "https://github.com/actions/runner/releases/download/v${ver}/actions-runner-linux-x64-${ver}.tar.gz"
tar xzf runner.tar.gz && rm -f runner.tar.gz && chown -R runner:runner /home/runner/actions-runner
# installdependencies.sh intentionally skipped (needs apt; required libs already present).
sleep 3
echo "PROVISION_OK docker=$(systemctl is-active docker) ver=${ver}"
')
echo "$PROV" | tail -3
echo "$PROV" | grep -q "PROVISION_OK docker=active" || { echo "ERROR: provisioning failed (see above)"; exit 1; }

echo "==> Minting a runner registration token (short-lived)"
TOKEN="$(gh api -X POST "repos/$REPO/actions/runners/registration-token" --jq .token)"
[ -n "$TOKEN" ] || { echo "ERROR: failed to mint registration token"; exit 1; }

echo "==> Registering + starting the runner as a service"
REG=$(rc "
set -e
cd /home/runner/actions-runner
sudo -u runner ./config.sh --unattended --replace \
  --url 'https://github.com/$REPO' --token '$TOKEN' \
  --name '$VM_NAME' --labels '$LABELS' --work _work
./svc.sh install runner
./svc.sh start
sleep 4; ./svc.sh status | head -6
echo REGISTER_DONE
")
echo "$REG" | tail -8
echo "$REG" | grep -q REGISTER_DONE || { echo "ERROR: registration failed (see above)"; exit 1; }

echo "==> Verifying the runner is online in GitHub"
sleep 8
gh api "repos/$REPO/actions/runners" --jq '.runners[] | {name, status, labels: [.labels[].name]}'

cat <<EOF

✅ Runner deployed + online. CI (.github/workflows/ci.yml) already targets
   'runs-on: [self-hosted, linux, x64]'.

Cost note: $VM_SIZE runs ~24x7. To pause billing when idle:
   az vm deallocate -g $RG -n $VM_NAME      # stop (no compute charge; CI offline)
   az vm start      -g $RG -n $VM_NAME      # resume (start before relying on CI)
EOF
