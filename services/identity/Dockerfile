# Local identity issuer (RS256 + JWKS) and Kong-config renderer.
# Build context is the repo root so the canonical gateway config
# (services/gateway/kong.yml) can be baked in as the render template.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/identity/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/identity/issuer.py ./issuer.py
COPY services/gateway/kong.yml ./kong.yml.tmpl

EXPOSE 8081
CMD ["python", "issuer.py"]
