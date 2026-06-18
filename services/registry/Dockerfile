# Source registry / control-plane (powers the onboarding wizard).
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/registry/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/registry/app.py ./app.py
EXPOSE 8095
CMD ["python", "app.py"]
