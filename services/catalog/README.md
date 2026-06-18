# catalog — FastAPI marketplace catalog

`GET /catalog` + `GET /catalog/{id}` returning `{title, owner, classification,
openapi_url (via Kong), request_path, sample_query}` from `catalog.json` +
`data/classification.yml`.

> [!NOTE]
> Build per PRP §6/§8 Phase 4.
