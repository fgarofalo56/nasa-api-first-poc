# mcp — MCP server (agent consumer)

One MCP tool `query_supply_risk(program, min_delay)`: gets a token from identity,
calls Kong, returns the ranked rows. Document how to point an MCP host
(e.g. Claude Desktop) at it.

```mermaid
flowchart LR
    host["MCP host<br/>(e.g. Claude Desktop)"] --> mcp["mcp server<br/>query_supply_risk()"]
    mcp --> id["identity (token)"]
    mcp --> kong["Kong Gateway"]
    kong --> dab["Data API Builder"]
```

> [!NOTE]
> Build per PRP §6/§8 Phase 5.
