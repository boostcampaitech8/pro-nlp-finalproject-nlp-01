#!/bin/bash
# DO NOT set -e here so we can capture failures more gracefully
# set -e 

echo "=== System Information ==="
python --version
pip list | grep -E "fastapi|uvicorn|sqlalchemy|psycopg|alembic"

echo "=== Environment Check ==="
echo "PORT: $PORT"
echo "PYTHONPATH: $PYTHONPATH"
echo "DATABASE_URL (domain): $(echo $DATABASE_URL | sed 's/.*@//' | sed 's/?.*/ /')"
echo "HF_TOKEN length: ${#HF_TOKEN}"

echo "=== Verifying Database Connectivity ==="
# We use a python script that prints exactly what's happening
python << END
try:
    import os
    import sys
    # Add /app to sys.path just in case
    sys.path.append(os.getcwd())
    
    from app.db.database import engine
    from sqlalchemy import text
    
    print("Attempting to connect to DB and run 'SELECT 1'...")
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print(f"Connectivity check successful: {result.scalar()}")
except Exception as e:
    print(f"FAILED Connectivity Check: {str(e)}")
    import traceback
    traceback.print_exc()
END

echo "=== Running Alembic Migrations ==="
alembic upgrade head
ALEMBIC_STATUS=$?

if [ $ALEMBIC_STATUS -ne 0 ]; then
    echo "ERROR: Migrations failed with exit code $ALEMBIC_STATUS."
else
    echo "Migrations check completed."
fi

echo "=== Starting Uvicorn ==="
# Using 0.0.0.0 is critical, and $PORT is provided by Cloud Run
echo "Executing: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}

