FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies for psycopg2 and PDF processing
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Build from Root Context
COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy Shared Code
COPY common/ ./common/

# Copy Jobs Code
COPY jobs/ ./jobs/

# Copy Backend Code
COPY backend/ .

ENV PYTHONPATH=/app
# Cloud Run injects the PORT environment variable (default 8080)
# Enabling debug logs to see exactly where it stops
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --log-level debug"]
