# gateway — Kong Gateway OSS (DB-less)

Declarative `kong.yml`: service → DAB, routes, plugins `jwt` + `rate-limiting` +
`prometheus` + `correlation-id` (+ one OWASP-API control). Two consumers for
per-consumer metering.

```mermaid
flowchart LR
    client["Client / MCP"] --> kong["Kong Gateway<br/>(jwt · rate-limit · prometheus · correlation-id)"]
    kong --> dab["Data API Builder"]
    dab --> pg[("Postgres")]
```

> [!NOTE]
> Build per PRP §6/§8 Phase 3.
