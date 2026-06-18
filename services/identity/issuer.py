"""Minimal local OIDC/JWT issuer — stands in for Microsoft Entra ID.

Responsibilities:
  * generate (and persist) an RS256 keypair,
  * publish a JWKS (`/.well-known/jwks.json`) and the raw public PEM,
  * mint short-lived RS256 bearer tokens per consumer (`POST /token`), and
  * render the live public key into Kong's declarative config on startup, so the
    gateway validates these exact tokens (no key material is ever committed).

The token's `client_id` claim is the consumer id; Kong's jwt plugin uses it
(`key_claim_name=client_id`) to map the call to a consumer for per-consumer metering.
"""

from __future__ import annotations

import base64
import contextlib
import logging
import os
import time
from pathlib import Path

import jwt
import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s identity %(message)s")
log = logging.getLogger("identity")

ISSUER = os.environ.get("JWT_ISSUER", "https://issuer.local")
AUDIENCE = os.environ.get("JWT_AUDIENCE", "artemis-api")
PORT = int(os.environ.get("ISSUER_PORT", "8081"))
RATE_LIMIT = os.environ.get("RATE_LIMIT_PER_MINUTE", "60")
KEY_DIR = Path(os.environ.get("KEY_DIR", "/shared/keys"))
KONG_TEMPLATE = Path(os.environ.get("KONG_TEMPLATE", "/app/kong.yml.tmpl"))
KONG_RENDERED = Path(os.environ.get("KONG_RENDERED", "/shared/kong.yml"))
KID = "artemis-local-key-1"
TOKEN_TTL = int(os.environ.get("TOKEN_TTL_SECONDS", "3600"))

# The two demo consumers (per-consumer metering at the gateway).
ALLOWED_CONSUMERS = {"analyst", "artemis-agent"}

_state: dict = {}


def _load_or_create_keys() -> tuple[rsa.RSAPrivateKey, str]:
    # A provided key (env) takes precedence — used in Azure so the baked gateway config's
    # public key matches the issuer without a shared volume.
    env_pem = os.environ.get("JWT_PRIVATE_KEY_PEM")
    if env_pem:
        # accept raw PEM or base64-encoded PEM (ACA secrets dislike multi-line values)
        if "BEGIN" not in env_pem:
            env_pem = base64.b64decode(env_pem).decode()
        private_key = serialization.load_pem_private_key(env_pem.encode(), password=None)
        log.info("loaded RSA key from JWT_PRIVATE_KEY_PEM env")
        public_pem = (
            private_key.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode()
        )
        return private_key, public_pem
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    priv_path = KEY_DIR / "jwt-private.pem"
    if priv_path.exists():
        private_key = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
        log.info("loaded existing RSA key from %s", priv_path)
    else:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv_path.write_bytes(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        log.info("generated new RSA key -> %s", priv_path)
    public_pem = (
        private_key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return private_key, public_pem


def _render_kong(public_pem: str) -> None:
    if not KONG_TEMPLATE.exists():
        log.warning("kong template %s not found; skipping render", KONG_TEMPLATE)
        return
    escaped = public_pem.strip().replace("\n", "\\n")
    rendered = (
        KONG_TEMPLATE.read_text(encoding="utf-8")
        .replace("__RSA_PUBLIC_KEY__", escaped)
        .replace("__RATE_LIMIT__", str(RATE_LIMIT))
    )
    KONG_RENDERED.parent.mkdir(parents=True, exist_ok=True)
    KONG_RENDERED.write_text(rendered, encoding="utf-8")
    log.info(
        "rendered Kong declarative config -> %s (rate-limit=%s/min)", KONG_RENDERED, RATE_LIMIT
    )


def _b64u(n: int) -> str:
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _jwks(public_key: rsa.RSAPublicKey) -> dict:
    nums = public_key.public_numbers()
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": KID,
                "n": _b64u(nums.n),
                "e": _b64u(nums.e),
            }
        ]
    }


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    private_key, public_pem = _load_or_create_keys()
    _state["private_key"] = private_key
    _state["public_pem"] = public_pem
    _render_kong(public_pem)
    yield


app = FastAPI(title="Artemis local identity issuer", version="0.1.0", lifespan=lifespan)

# Local demo: allow the browser SPA (any local origin) to request tokens.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TokenRequest(BaseModel):
    consumer: str = "analyst"


@app.get("/healthz")
def healthz():
    return {"status": "ok", "issuer": ISSUER}


@app.get("/.well-known/jwks.json")
def jwks():
    return _jwks(_state["private_key"].public_key())


@app.get("/public.pem", response_class=PlainTextResponse)
def public_pem():
    return _state["public_pem"]


@app.post("/token")
def issue_token(req: TokenRequest):
    if req.consumer not in ALLOWED_CONSUMERS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown consumer '{req.consumer}'; choose one of {sorted(ALLOWED_CONSUMERS)}",
        )
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": req.consumer,
        "client_id": req.consumer,  # Kong maps consumer via this claim
        "iat": now,
        "nbf": now,
        "exp": now + TOKEN_TTL,
    }
    token = jwt.encode(claims, _state["private_key"], algorithm="RS256", headers={"kid": KID})
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": TOKEN_TTL,
        "consumer": req.consumer,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
