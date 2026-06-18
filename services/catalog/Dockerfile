# Marketplace catalog service. Build context is the repo root so the catalog can
# merge the canonical data/classification.yml (classify-before-exposure).
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/catalog/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/catalog/app.py ./app.py
COPY services/catalog/catalog.json ./catalog.json
COPY data/classification.yml ./classification.yml

EXPOSE 8080
CMD ["python", "app.py"]
