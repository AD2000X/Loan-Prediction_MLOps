# Loan Prediction MLOps Platform

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103.0-green.svg)](https://fastapi.tiangolo.com/)
[![MLflow](https://img.shields.io/badge/MLflow-2.13.2-blue.svg)](https://mlflow.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Production-grade loan prediction platform with MLflow model registry, DVC-backed datasets, FastAPI inference service, and monitoring/drift tooling.

## What's Included

- **MLOps**: MLflow experiment tracking and registry, Hyperopt HPO, SHAP explainability, Fairlearn fairness checks, DVC-backed datasets (S3 remote).
- **API**: FastAPI service on port 8005 with `/health`, `/prediction_api`, `/batch_prediction`, `/model_info`, `/list_models`, and `/metrics` (Prometheus).
- **Monitoring**: Prometheus + Grafana stack (`monitoring/docker-compose.yml`) and Evidently-based Streamlit drift app (`drift_monitoring/app_v1.py`).
- **Deployment**: Dockerfile that syncs MLflow artifacts from `s3://loanpred-mlops-20251118-120330/mlruns/`, Kubernetes manifests in `k8s/`, and GitHub Actions CI/CD (`.github/workflows/cicd.yml`).

## Repository Layout

```
Loan-Prediction_MLOps/
- .dvc/                   # DVC configuration (remote: s3://loanpred-mlops-20251118-120330)
- .github/workflows/      # CI/CD pipelines (cicd, docs-check, OIDC test)
- docs/                   # Setup, API, monitoring, CI/CD, infra guides
- drift_monitoring/       # Evidently Streamlit drift app + Dockerfile
- grafana/ , prometheus/  # Provisioning for monitoring stack
- k8s/                    # Kubernetes manifests for EKS deployment
- monitoring/             # docker-compose for Prometheus + Grafana
- prediction_model/       # Training, preprocessing, inference, config
- scripts/                # Helper scripts (DVC push, Docker build, EKS auth)
- tests/                  # API and prediction tests
- Dockerfile              # Production image (port 8005)
- datasets.dvc            # DVC tracking for datasets/ (pulled from S3)
- main.py                 # FastAPI entrypoint
- requirements*.txt       # Dependencies
```

## Prerequisites

- Python 3.11+
- pip
- Docker + Docker Compose (for monitoring)
- AWS CLI with access to the S3 bucket `<your S3_BUCKET_NAME>` (for data/artifacts)
- DVC with S3 support: `pip install dvc[s3]`

## Setup

1) Clone and create a virtual environment
```bash
git clone https://github.com/your-org/Loan-Prediction_MLOps.git
cd Loan-Prediction_MLOps

# venv (Linux/Mac)
python -m venv venv && source venv/bin/activate
# venv (Windows)
python -m venv venv && venv\Scripts\activate
```

2) Install dependencies
```bash
pip install -r requirements.txt
# Optional: development tooling
pip install -r requirements-dev.txt
```

3) Configure environment variables
```bash
cp .env.example .env
# Key variables from .env.example / code defaults:
# MLFLOW_TRACKING_URI=./mlruns          # File-based MLflow tracking by default
# MODEL_STAGE=Production                # Which stage the API serves
# API_PORT=8005
# AWS_REGION=<your AWS_REGION>
# S3_BUCKET_NAME=<your S3_BUCKET_NAME>
# DVC_REMOTE=<s3://your S3_BUCKET_NAME-your-unique-id/datasets>
# DRIFT_S3_BUCKET=<your S3_BUCKET_NAME-your-unique-id>
```

4) Pull datasets with DVC (requires AWS credentials)
```bash
aws configure                           # Ensure access to <your AWS_REGION>
dvc pull                                # Uses remote 'myremote' from .dvc/config
```
The default DVC remote points to `<your S3_BUCKET_NAME>`.

5) (Optional) Download existing MLflow runs/models
```bash
aws s3 sync s3://<your S3_BUCKET_NAME>/mlruns/ ./mlruns/
```

## Model Training

Train models and log to MLflow (experiment `loan_prediction_model`):
```bash
python -m prediction_model.training_pipeline
```
- Reads data from `datasets/train.csv` and `datasets/test.csv` (DVC-managed).
- Logs metrics, SHAP plots, and models to `./mlruns` (or the URI in `MLFLOW_TRACKING_URI`).
- S3 bucket used for artifacts by default: `<your S3_BUCKET_NAME>` (see `prediction_model/config/config.py`).

## Run the API

Start FastAPI (serves the latest model stage via MLflow):
```bash
python main.py
# or: uvicorn main:app --host 0.0.0.0 --port 8005
```
Environment notes:
- Ensure `mlruns/` contains a trained model (train locally or sync from S3).
- `MODEL_STAGE` controls which stage to load (`Production` default).
- Metrics are exposed at `/metrics` for Prometheus scraping.

### Example requests

Single prediction:
```bash
curl -X POST http://localhost:8005/prediction_api \
  -H "Content-Type: application/json" \
  -d '{
    "Gender": "Male",
    "Married": "Yes",
    "Dependents": "0",
    "Education": "Graduate",
    "Self_Employed": "No",
    "ApplicantIncome": 5000,
    "CoapplicantIncome": 2000,
    "LoanAmount": 150,
    "Loan_Amount_Term": 360,
    "Credit_History": 1,
    "Property_Area": "Urban"
  }'
```

Batch prediction (CSV upload):
```bash
curl -X POST http://localhost:8005/batch_prediction \
  -F "file=@batch_data.csv" \
  -o predictions.csv
```

Model info:
```bash
curl "http://localhost:8005/model_info?stage=Production"
```

## Monitoring and Drift

- Prometheus/Grafana:
  ```bash
  cd monitoring
  docker-compose up -d
  ```
  - Prometheus: http://localhost:9090
  - Grafana: http://localhost:3000 (admin/admin by default)
- The API exposes `/metrics` (uses `prometheus_fastapi_instrumentator`).
- Data drift UI:
  ```bash
  cd drift_monitoring
  pip install -r requirements.txt
  streamlit run app_v1.py
  ```
  Set `DRIFT_S3_BUCKET` if pulling batches from S3; defaults are in `drift_monitoring/config.py`.
- Script `collect_k8s_predictions.py` can collect sample predictions from a cluster endpoint for drift analysis.

## Data and Artifact Management

- Datasets are tracked via DVC (`datasets.dvc`). Remote `myremote` is defined in `.dvc/config`:
  - URL: `s3://<your S3_BUCKET_NAME>`
  - Region: `eu-west-2`
- Common commands:
  ```bash
  dvc pull            # fetch datasets
  dvc add datasets/   # track updated data
  dvc push            # push data to S3
  ```
- MLflow artifacts: default bucket `<your S3_BUCKET_NAME>` (Docker startup script syncs `mlruns/` from there).

## Docker and Deployment

- Build locally:
  ```bash
  scripts\build_docker_local.bat          # Windows helper
  # or
  docker build -t loan-prediction:local .
  ```
- Run container:
  ```bash
  docker run -p 8005:8005 \
    -e MLFLOW_TRACKING_URI="http://host.docker.internal:5000" \
    loan-prediction:local
  ```
  The image syncs `mlruns/` from S3 on startup (see Dockerfile `start.sh`).
- Kubernetes manifests are in `k8s/` (deployments, services, ServiceMonitor, namespace/auth helpers).
- GitHub Actions CI/CD (`.github/workflows/cicd.yml`) trains, validates metrics, pushes to ECR, and deploys to EKS using DVC data from the same S3 remote.

## Testing

Tests live in `tests/`:
- Unit/API tests target the FastAPI app and prediction helpers.
- Integration tests are guarded by a `--run-integration` flag in the test files; the flag is not currently defined via `pytest_addoption`, so you need to add that option or adjust the skip logic before running pytest with the current codebase.
- After adding the flag, run:
  ```bash
  pytest tests/ -v                   # fast checks
  pytest tests/ -v --run-integration # requires MLflow models present in mlruns/
  ```

## Documentation

- `docs/SETUP.md`: Detailed environment setup
- `docs/API.md`: Endpoint contract and schemas
- `docs/MONITORING.md`: Metrics, Grafana, Fairlearn, MLflow instructions
- `docs/CI_CD_WORKFLOW.md`: CI/CD pipeline breakdown
- `docs/infra/*.md`: ECR, EKS, Prometheus, Grafana, and S3 notes

## License

MIT License. See `LICENSE`.
