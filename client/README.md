# client — Python CLI

`query_supply_risk.py --program Artemis-3 --min-delay 30`: bearer-token flow → calls
Kong → prints the ranked answer **and** the gateway correlation id (proof the call
went through the gateway).

```bash
python query_supply_risk.py --program Artemis-3 --min-delay 30
```

> [!NOTE]
> Build per PRP §6/§8 Phase 5.
