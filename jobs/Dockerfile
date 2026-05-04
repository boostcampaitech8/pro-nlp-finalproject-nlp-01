FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY jobs/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy common and jobs
COPY common/ ./common/
COPY jobs/ ./jobs/

# Set Python path to find 'common'
ENV PYTHONPATH=/app

# Entrypoint is the job runner
# Arguments like --task and --id will be passed by Cloud Run Job execution or local trigger
ENTRYPOINT ["python", "jobs/run_job.py"]
