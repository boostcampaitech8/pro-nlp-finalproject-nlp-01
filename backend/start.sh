#!/bin/bash
set -e

echo "=== Pro-NLP Backend Startup ==="
echo "PORT: $PORT"

echo "=== Starting Uvicorn Server ==="
# Using 0.0.0.0 is critical for Cloud Run
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}



