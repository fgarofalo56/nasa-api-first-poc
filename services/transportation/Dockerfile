# Stand-in for an existing external DAB API (DOT transportation). Internal-only.
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/transportation/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/transportation/app.py ./app.py
EXPOSE 8200
CMD ["python", "app.py"]
