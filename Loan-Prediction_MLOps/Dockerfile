# Loan Prediction - MLOps Dockerfile
# Production-ready container with S3-based model artifact storage

FROM python:3.11-slim

# Environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_STAGE=Production \
    AWS_DEFAULT_REGION=eu-west-2

# Set working directory
WORKDIR /app

# Install system dependencies required for ML libraries and AWS CLI
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        libgtk2.0-0 \
        curl \
        unzip \
    && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf aws awscliv2.zip \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py run.py ./
COPY prediction_model ./prediction_model

# Create startup script to sync MLflow data from S3
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Syncing MLflow tracking data from S3..."\n\
aws s3 sync s3://loanpred-mlops-20251118-120330/mlruns/ /app/mlruns/ || echo "Warning: Could not sync from S3, using local mlruns"\n\
echo "Starting FastAPI application..."\n\
exec python main.py' > /app/start.sh \
    && chmod +x /app/start.sh

# Expose FastAPI service port
EXPOSE 8005

# Health check for Kubernetes
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8005/health').raise_for_status()" || exit 1

# Run startup script which syncs from S3 and starts application
CMD ["/app/start.sh"]
