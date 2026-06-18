# Seeder job: generates the synthetic CSVs, loads Postgres, applies classification.
# Build context is the repo root (needs data/synthetic_data.py + data/classification.yml).
FROM python:3.11-slim

WORKDIR /app

COPY services/seeder/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/seeder/seed.py services/seeder/schema.sql ./
COPY data/synthetic_data.py ./synthetic_data.py
COPY data/classification.yml ./classification.yml

ENV SEED_OUT_DIR=/tmp/artemis_out
CMD ["python", "seed.py"]
