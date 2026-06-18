# How zero-move is proven in this POC

The system-of-record data (PostgreSQL) and the auto-API (Data API Builder) attach
**only** to the `internal` Docker network. Clients, the catalog, and the MCP server
attach to the `edge` network. The **only** bridge between them is the Kong gateway.

Therefore the only path to the data is **through the gateway** — there is no route by
which a client can read Postgres or DAB directly. The data is never copied out; the
gateway brokers, authenticates, throttles, and meters every call.

## The concrete configuration (`docker-compose.yml`)

```yaml
networks:
  internal:
    internal: true     # no egress; postgres + dab live here
  edge:
    driver: bridge

postgres: { networks: [internal] }            # no `ports:` — no host mapping
dab:      { networks: [internal] }            # no `ports:` — no host mapping
kong:     { networks: [internal, edge] }      # the ONLY service on both
catalog:  { networks: [edge] }
mcp:      { networks: [edge] }
```

- Postgres and DAB declare **no `ports:`** — they are never published to the host.
- `internal: true` means that network has **no outbound** route either.
- Kong is the single service attached to both networks; it proxies `edge → internal`
  only for the routes it exposes, and only after JWT + rate-limit + OWASP checks pass.

## What the test proves (`tests/test_zero_move.py`)

Run via `make test` with the stack up:

1. **Edge cannot reach the SoR.** A throwaway container on the `edge` network runs
   `nc -z postgres 5432` and `nc -z dab 5000` — both fail (the names do not even
   resolve on `edge`).
2. **Edge can reach Kong.** The same probe to `kong 8000` succeeds — Kong is the one
   path.
3. **No host ports.** `docker compose port postgres 5432` and `… dab 5000` return no
   published binding.
4. **The data still answers through Kong.** A bearer-authenticated
   `GET /api/SupplyRisk` returns rows — the governed path works.

If any client could read Postgres or DAB directly, assertions (1) or (3) would fail.
This is the difference between *claiming* zero-move and *proving* it.
