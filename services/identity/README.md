# identity — local OIDC/JWT issuer (stands in for Microsoft Entra ID)

Minimal RS256 issuer: `GET /.well-known/jwks.json` + `POST /token`. Kong validates
incoming tokens against the published JWKS.

> [!NOTE]
> Build per PRP §3/§8 Phase 3.
