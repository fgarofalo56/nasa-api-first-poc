# identity — local OIDC/JWT issuer (stands in for Microsoft Entra ID)
Minimal RS256 issuer: `/.well-known/jwks.json` + `POST /token`. Kong validates against
the JWKS. Build per PRP §3/§8 Phase 3.
