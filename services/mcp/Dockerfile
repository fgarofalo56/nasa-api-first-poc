# MCP server (agent consumer). Reaches the gateway over the edge network; never the DB.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/mcp/server.py ./server.py
COPY services/mcp/smoke_client.py ./smoke_client.py

EXPOSE 8090
CMD ["python", "server.py"]
