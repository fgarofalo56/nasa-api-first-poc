#!/usr/bin/env bash
# End-to-end demo runner (make demo). Assumes the core stack is already up + seeded.
set -euo pipefail
cd "$(dirname "$0")/.."

# Resolve host ports: explicit env > .env value > default. (We read .env field-by-field
# rather than sourcing it, because values like the DAB connection string contain ';'.)
get_env() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- || true; }
KONG_PROXY_PORT="${KONG_PROXY_PORT:-$(get_env KONG_PROXY_PORT)}"; KONG_PROXY_PORT="${KONG_PROXY_PORT:-8000}"
ISSUER_PORT="${ISSUER_PORT:-$(get_env ISSUER_PORT)}"; ISSUER_PORT="${ISSUER_PORT:-8081}"
MCP_PORT="${MCP_PORT:-$(get_env MCP_PORT)}"; MCP_PORT="${MCP_PORT:-8090}"

# 127.0.0.1 (not "localhost") avoids IPv6/IPv4 ambiguity on some hosts.
export KONG_URL="http://127.0.0.1:${KONG_PROXY_PORT}"
export IDENTITY_URL="http://127.0.0.1:${ISSUER_PORT}"
export MCP_URL="http://127.0.0.1:${MCP_PORT}/mcp"
PY="${PY:-python}"

echo "============================================================"
echo "  NASA API-first zero-move demo - Artemis supply-chain"
echo "  (synthetic SAP procurement; data never leaves Postgres)"
echo "============================================================"

echo
echo "[1/4] No-token call is rejected at the gateway (expect 401):"
code="$(curl -s -o /dev/null -w '%{http_code}' "${KONG_URL}/api/SupplyRisk" || true)"
echo "      GET /api/SupplyRisk (no token)  ->  HTTP ${code}"

echo
echo "[2/4] Governed Python client answers the mission question THROUGH Kong:"
"$PY" client/query_supply_risk.py --program Artemis-3 --min-delay 30

echo "[3/4] An MCP agent gets the SAME governed answer over the MCP protocol:"
"$PY" services/mcp/smoke_client.py || echo "      (MCP smoke skipped - server not reachable)"

echo
echo "[4/4] Zero-move: Postgres + DAB sit on an internal network with no host ports;"
echo "      the ONLY path to the data is through Kong (proof: make test / test_zero_move.py)."
echo
echo "Done. With the observability profile up, open Grafana to see per-consumer traffic."
