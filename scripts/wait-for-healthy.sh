#!/usr/bin/env bash
# Block until every core service reports healthy (or time out).
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE="${COMPOSE:-docker compose}"
TIMEOUT="${1:-180}"
SERVICES="postgres dab identity kong catalog mcp"

echo "Waiting up to ${TIMEOUT}s for core services to become healthy..."
deadline=$(( $(date +%s) + TIMEOUT ))

while true; do
  all_ok=1
  for svc in $SERVICES; do
    cid="$($COMPOSE ps -q "$svc" 2>/dev/null || true)"
    if [ -z "$cid" ]; then all_ok=0; break; fi
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo missing)"
    if [ "$status" != "healthy" ]; then all_ok=0; break; fi
  done
  if [ "$all_ok" = "1" ]; then
    echo "All core services healthy."
    exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "ERROR: timed out waiting for services to become healthy." >&2
    $COMPOSE ps
    exit 1
  fi
  sleep 3
done
