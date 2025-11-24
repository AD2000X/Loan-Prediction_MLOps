# Loan Prediction MLOps Platform

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103.0-green.svg)](https://fastapi.tiangolo.com/)
[![MLflow](https://img.shields.io/badge/MLflow-2.13.2-blue.svg)](https://mlflow.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Production-grade loan prediction MLOps platform implementing complete machine learning lifecycle management, monitoring, and deployment.

## Features

### MLOps Capabilities

- **Model Registry & Version Management**: MLflow Model Registry
- **Experiment Tracking**: Automatic logging of hyperparameters, metrics, and models
- **Model Deployment Strategies**: Support for blue-green deployment, canary deployment, A/B testing
- **Data Version Control**: DVC + S3
- **Continuous Integration/Continuous Deployment**: GitHub Actions → AWS EKS

### Monitoring & Observability

- **Performance Monitoring**: Prometheus + Grafana
- **Data Drift Detection**: Evidently.ai + Streamlit
- **Model Explainability**: SHAP values
- **Fairness Analysis**: Fairlearn
- **Real-time Metrics**: Request volume, latency, error rate, prediction distribution

### Machine Learning

- **Models**: XGBoost (Production) + LightGBM (Staging)
- **Hyperparameter Optimization**: Hyperopt (Tree-structured Parzen Estimator)
- **Feature Engineering**: Custom sklearn transformers
- **Performance Metrics**: F1-Score, Accuracy, Recall, Precision

### API Service

- **Framework**: FastAPI
- **Endpoints**: Single prediction, batch prediction, model information query
- **Features**: CORS, file upload, S3 integration
- **Documentation**: Auto-generated OpenAPI (Swagger/ReDoc)

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- AWS CLI (for deployment)
- MLflow Server (local file backend)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/Loan-Prediction_MLOps.git
cd Loan-Prediction_MLOps

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### Configure Environment Variables

```bash
# Copy environment variable template
cp .env.example .env

# Edit .env file
export MLFLOW_TRACKING_URI="http://localhost:5000"
export AWS_REGION="eu-west-2"
export S3_BUCKET_NAME="your-bucket-name"
```

### Run API

```bash
# Start FastAPI service
python main.py

# Access API documentation
# http://localhost:8005/docs
```

### Start Monitoring System

```bash
cd monitoring
docker-compose up -d

# Access Grafana: http://localhost:3000 (admin/admin)
# Access Prometheus: http://localhost:9090
```

### Run Tests

```bash
# Basic tests (no MLflow required)
pytest tests/ -v

# Full tests (requires MLflow configuration)
pytest tests/ -v --run-integration
```

## Project Structure

```
Loan-Prediction_MLOps/
├── .github/workflows/          # CI/CD workflows
│   ├── cicd.yml                # Main deployment workflow
│   └── docs-check.yml          # Documentation checks
├── docs/                       # Documentation
│   ├── SETUP.md                # Environment setup guide
│   ├── API.md                  # API documentation
│   └── MONITORING.md           # Monitoring documentation
├── drift_monitoring/           # Data drift monitoring
│   ├── app_v1.py               # Streamlit application
│   ├── Dockerfile              # Containerization
│   └── README.md               # Usage instructions
├── monitoring/                 # Prometheus + Grafana
│   ├── docker-compose.yml      # One-click startup
│   ├── prometheus/             # Prometheus configuration
│   └── grafana/                # Grafana dashboards
├── prediction_model/           # ML core code
│   ├── config/                 # Configuration
│   ├── processing/             # Data processing
│   ├── training_pipeline.py    # Training workflow
│   └── predict.py              # Inference code
├── tests/                      # Tests
│   ├── test_api.py             # API tests
│   └── test_prediction.py      # Prediction logic tests
├── k8s/                        # Kubernetes configuration
│   ├── deployment.yml          # EKS deployment
│   └── services.yml            # Service configuration
├── main.py                     # FastAPI entry point
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── pytest.ini                  # Test configuration
└── README.md                   # This file
```

## API Usage Examples

### Single Prediction

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

**Response**:
```json
{
  "prediction": "Y",
  "model_version": "1",
  "model_type": "XGBoost",
  "model_stage": "Production"
}
```

### Batch Prediction

```bash
curl -X POST http://localhost:8005/batch_prediction \
  -F "file=@batch_data.csv" \
  -o predictions.csv
```

### View Model Information

```bash
curl http://localhost:8005/model_info?stage=Production
```

## Train New Model

```bash
# Set MLflow Tracking URI
export MLFLOW_TRACKING_URI="http://localhost:5000"

# Run training workflow
python prediction_model/training_pipeline.py

# View MLflow UI
# http://localhost:5000
```

Training workflow will:
1. Load and split data
2. Optimize hyperparameters using Hyperopt (5 trials)
3. Train XGBoost and LightGBM models
4. Generate SHAP explanation plots
5. Calculate fairness metrics
6. Register models to MLflow Registry

## Deployment

### Local Deployment (Docker)

```bash
# Build image
docker build -t loan-prediction:latest .

# Run container
docker run -p 8005:8005 \
  -e MLFLOW_TRACKING_URI="http://host.docker.internal:5000" \
  loan-prediction:latest
```

### AWS EKS Deployment

The project includes a complete CI/CD workflow that automatically deploys when pushing to the `main` branch:

```bash
git add .
git commit -m "Update model"
git push origin main
```

GitHub Actions will:
1. Build Docker image
2. Push to Amazon ECR
3. Deploy to EKS cluster (3 replicas)
4. Wait for health checks

## Monitoring

### Grafana Dashboard

Access http://localhost:3000 to view:

- Request rate (QPS)
- Request latency (P50, P95, P99)
- Error rate
- Prediction distribution (approved vs rejected)
- Model version usage

### Data Drift Monitoring

```bash
cd drift_monitoring
streamlit run app_v1.py
```

Access http://localhost:8501 to view data drift reports.

## Documentation

- [Environment Setup](docs/SETUP.md): Complete installation and configuration guide
- [API Documentation](docs/API.md): Detailed description of all API endpoints
- [Monitoring Documentation](docs/MONITORING.md): Prometheus & Grafana usage guide
- [Swagger UI](http://localhost:8005/docs): Interactive API documentation

## Technology Stack

| Category | Technology |
|----------|------------|
| ML Framework | XGBoost, LightGBM, scikit-learn |
| MLOps | MLflow, DVC, SHAP, Fairlearn |
| API | FastAPI, Pydantic, Uvicorn |
| Monitoring | Prometheus, Grafana, Evidently |
| Visualization | Streamlit, Matplotlib |
| Data | Pandas, NumPy |
| Optimization | Hyperopt |
| Containerization | Docker, Kubernetes |
| Cloud Services | AWS (EKS, ECR, S3) |
| CI/CD | GitHub Actions |
| Testing | pytest |

## Performance Metrics

### API Performance

- Latency: P95 < 200ms
- Throughput: ~100 QPS (single instance)
- Availability: 99.9% (3 replicas on EKS)

### Model Performance

- XGBoost (Production): F1-Score ~0.82
- LightGBM (Staging): F1-Score ~0.83
- Training Time: ~5-10 minutes (including HPO)

## Development

### Code Style

```bash
# Format code
black .

# Check code quality
flake8 .

# Sort imports
isort .
```

### Run Tests

```bash
# Quick tests (skip integration tests)
pytest tests/ -m "not integration"

# Full tests
pytest tests/ --run-integration --cov=prediction_model --cov=main

# Generate coverage report
pytest tests/ --cov-report=html
```

### Submit Code

```bash
# Create branch
git checkout -b feature/your-feature

# Commit changes
git add .
git commit -m "Add: your feature description"

# Push to remote
git push origin feature/your-feature
```

## Cost Estimation (AWS)

| Service | Configuration | Monthly Cost (eu-west-2) |
|---------|--------------|--------------------------|
| EKS Cluster | Control plane | $73 |
| EC2 Nodes | 3x t3.medium | ~$90 |
| ECR | Storage + Transfer | ~$5 |
| S3 | 10GB | ~$0.23 |
| ALB | Load balancer | ~$22 |
| Total | | ~$190/month |

Optimization Suggestions:
- Use Spot Instances to save ~70%
- Use Fargate Spot for development environments
- Scale down to 1 replica during non-business hours

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the project
2. Create a feature branch (git checkout -b feature/AmazingFeature)
3. Commit your changes (git commit -m 'Add some AmazingFeature')
4. Push to the branch (git push origin feature/AmazingFeature)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Email: your-email@example.com
- Issues: GitHub Issues (https://github.com/your-org/Loan-Prediction_MLOps/issues)
- Documentation: docs/

## Acknowledgments

- MLflow (https://mlflow.org/) - Experiment tracking and model management
- FastAPI (https://fastapi.tiangolo.com/) - Modern Python web framework
- Evidently (https://evidentlyai.com/) - ML monitoring tools
- Prometheus (https://prometheus.io/) & Grafana (https://grafana.com/) - Monitoring and visualization

---

If this project helps you, please give it a Star!
