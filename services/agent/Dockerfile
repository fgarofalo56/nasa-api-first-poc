# Mission agent — an MCP host that answers grounded questions over the gateway data.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/agent/agent.py ./agent.py

EXPOSE 8110
CMD ["python", "agent.py"]
