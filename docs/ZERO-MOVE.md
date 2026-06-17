# How zero-move is proven in this POC

The system-of-record data (PostgreSQL) and the auto-API (Data API Builder) attach
**only** to the `internal` Docker network. Clients, the catalog, and the MCP server
attach to the `edge` network. The **only** bridge between them is the Kong gateway.

Therefore the only path to the data is **through the gateway** — there is no route by
which a client can read Postgres or DAB directly. `tests/test_zero_move.py` asserts
this: a direct connection attempt to Postgres / DAB from the client network fails,
while the same query succeeds through Kong. The data is never copied out; the gateway
brokers, authenticates, throttles, and meters every call.

> _Expand with the concrete network config + test assertions during the build._
