# Microsoft Data API Builder over Postgres, config-driven (no hand-written API).
# We extend the official image only to add `curl` for the compose healthcheck and to
# bake in dab-config.json. The connection string is injected via @env at runtime.
FROM mcr.microsoft.com/azure-databases/data-api-builder:latest

USER root
# The base image is Azure Linux (tdnf) or Debian (apt) depending on tag — try both.
RUN (tdnf install -y curl && tdnf clean all) \
    || (apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*)

COPY dab-config.json /App/dab-config.json
