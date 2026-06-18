# seeder

Builds the synthetic Artemis CSVs (via `data/synthetic_data.py`), applies
`data/classification.yml` as Postgres column comments, and loads the four tables.

```mermaid
flowchart LR
    gen["synthetic_data.py<br/>(generate CSVs)"] --> load["seed.py<br/>(load 4 tables)"]
    cls["classification.yml"] --> load
    load --> pg[("Postgres<br/>system of record")]
```

> [!NOTE]
> Build per PRP §4 (`schema.sql`, `seed.py`, `Dockerfile`) + §7 Phase 1.
