# Security model

> _Fill in during the build (PRP §6/§9)._

- **Identity / auth:** OAuth2 bearer (RS256 JWT from the local issuer; stands in for
  Microsoft Entra ID). Kong's `jwt` plugin validates against the issuer JWKS; a request
  with no/invalid token is rejected at the edge and never reaches DAB.
- **Rate limiting / quota:** Kong `rate-limiting` (429 + `Retry-After`).
- **OWASP API Top 10 at the gateway:** document which controls map to which risks
  (validate-jwt analogue, rate-limit, IP filtering, request-termination guard).
- **Classify before exposure:** `data/classification.yml` labels are applied at seed and
  surfaced in the catalog — confidential records are governed differently from routine.
- **Secrets:** via `.env` (gitignored); no secrets in the repo.
