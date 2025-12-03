# Loan Prediction MLOps Project Architecture

```
+---------------------------------------------------------------------------------+
|                           END-TO-END MLOPS PIPELINE                             |
+---------------------------------------------------------------------------------+

+---------------+    +---------------+    +---------------+    +---------------+
|  1. DATA      |--->|  2. TRAINING  |--->|  3. REGISTRY  |--->|  4. DEPLOY    |
|  VERSIONING   |    |  PIPELINE     |    |  & STAGING    |    |  & SERVING    |
|  (DVC + S3)   |    |  (MLflow)     |    |  (MLflow)     |    |  (K8s)        |
+---------------+    +---------------+    +---------------+    +---------------+
                                                                      |
                                                                      v
                     +---------------+    +---------------+    +---------------+
                     |  7. DRIFT     |<---|  6. METRICS   |<---|  5. API       |
                     |  DETECTION    |    |  COLLECTION   |    |  SERVICE      |
                     |  (Evidently)  |    |  (Prometheus) |    |  (FastAPI)    |
                     +---------------+    +---------------+    +---------------+
```

---

## Phase 1: Data Versioning

### DVC + AWS S3 Pipeline

```
+-------------------------------------------------------------+
|                    DVC + AWS S3 Pipeline                     |
+-------------------------------------------------------------+
|                                                              |
|   Local Files              DVC Tracking         S3 Storage   |
|   +---------+             +---------+         +---------+    |
|   |datasets/|------------>|.dvc file|-------->|  S3     |    |
|   |train.csv|   dvc add   |(metadata)| dvc push| Bucket  |    |
|   |test.csv |             +---------+         +---------+    |
|   +---------+                  |                    |        |
|                                v                    v        |
|                          Git Commit            Data Store    |
|                       (Version Tracking)     (Actual Data)   |
+-------------------------------------------------------------+
```

### Process Description

- Raw loan data is stored in the `datasets/` directory
- DVC tracks data changes and generates `.dvc` metadata files
- Actual data is pushed to AWS S3 bucket (`s3://loanpred-mlops-20251118-120330`)
- Git only tracks `.dvc` files, ensuring data version synchronization with code version

### Key Configuration: `.dvc/config`

```
remote = myremote
url = s3://loanpred-mlops-20251118-120330
region = eu-west-2
```

---

## Phase 2: Training Pipeline

### Training Pipeline Flow

```
+-----------------------------------------------------------------------------+
|                         TRAINING PIPELINE FLOW                               |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +-------------+     +-------------+     +-------------+     +-----------+   |
|  | Load Data   |---->| Preprocess  |---->| Feature     |---->|  Train    |   |
|  | (datasets/) |     | Pipeline    |     | Engineering |     |  Models   |   |
|  +-------------+     +-------------+     +-------------+     +-----------+   |
|                             |                   |                   |        |
|                             v                   v                   v        |
|                      +-------------+     +-------------+     +-----------+   |
|                      |ModeImputer  |     |LogTransform |     | Hyperopt  |   |
|                      |MeanImputer  |     |FeatureAdder |     | Tuning    |   |
|                      |DropFeatures |     |LabelEncoder |     | (5 trials)|   |
|                      +-------------+     +-------------+     +-----------+   |
|                                                                     |        |
|                                                                     v        |
|  +-------------------------------------------------------------------------+ |
|  |                         MLflow Experiment Tracking                       | |
|  |  +-------------+  +-------------+  +-------------+  +-------------+      | |
|  |  | Parameters  |  |  Metrics    |  |  Artifacts  |  |   Model     |      | |
|  |  | max_depth   |  |  F1: 0.9286 |  |  pipeline   |  |  Signature  |      | |
|  |  | n_estimators|  |  Acc: 0.9048|  |  .pkl file  |  |  Schema     |      | |
|  |  | learning_rate| |  Recall     |  |             |  |             |      | |
|  |  +-------------+  +-------------+  +-------------+  +-------------+      | |
|  +-------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------+
```

### Preprocessing Steps

| Step | Processor | Function |
|------|-----------|----------|
| 1 | ModeImputer | Fill missing values for categorical features (mode) |
| 2 | MeanImputer | Fill missing values for numerical features (mean) |
| 3 | DropFeatures | Remove unnecessary features |
| 4 | DomainProcessing | Business logic feature processing |
| 5 | LogTransforms | Apply log transformation to skewed features (using log1p to handle zeros) |
| 6 | CustomLabelEncoder | Encode categorical features |

### Dual Model Training Strategy

```
+--------------------------------------------------------+
|              BLUE-GREEN MODEL ARCHITECTURE              |
+--------------------------------------------------------+
|                                                         |
|   XGBoost (Production)          LightGBM (Staging)      |
|   +------------------+          +------------------+    |
|   | Version 1        |          | Version 2        |    |
|   | F1: 0.8966       |          | F1: 0.9286       |    |
|   | Accuracy: 0.8571 |          | Accuracy: 0.9048 |    |
|   | Stage: Production|          | Stage: Staging   |    |
|   +------------------+          +------------------+    |
|           |                            |                |
|           v                            v                |
|   Handles 100% Traffic         Ready for Canary Test    |
|                                                         |
+--------------------------------------------------------+
```

---

## Phase 3: Model Registry & Version Management

### MLflow Model Registry

```
+-----------------------------------------------------------------------------+
|                          MLFLOW MODEL REGISTRY                               |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Model: "LoanPrediction"                                                     |
|  +-------------------------------------------------------------------------+ |
|  |                                                                          | |
|  |   Version 1 (XGBoost)              Version 2 (LightGBM)                  | |
|  |   +------------------+             +------------------+                  | |
|  |   | Stage: Production|             | Stage: Staging   |                  | |
|  |   | Run ID: 88efdd31 |             | Run ID: ac1b3963 |                  | |
|  |   | Created: 2025-11 |             | Created: 2025-11 |                  | |
|  |   |                  |             |                  |                  | |
|  |   | Metrics:         |             | Metrics:         |                  | |
|  |   | - F1: 0.8966     |             | - F1: 0.9286     |                  | |
|  |   | - Accuracy: 0.857|             | - Accuracy: 0.905|                  | |
|  |   +------------------+             +------------------+                  | |
|  |            |                               |                              | |
|  |            v                               v                              | |
|  |   +------------------+             +------------------+                  | |
|  |   | Artifacts:       |             | Artifacts:       |                  | |
|  |   | - model.pkl      |             | - model.pkl      |                  | |
|  |   | - requirements   |             | - requirements   |                  | |
|  |   | - MLmodel        |             | - MLmodel        |                  | |
|  |   +------------------+             +------------------+                  | |
|  |                                                                          | |
|  +-------------------------------------------------------------------------+ |
|                                                                              |
|  Stage Transitions:                                                          |
|  None --> Staging --> Production --> Archived                                |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### Model Lifecycle Management

```python
# Model stage transition workflow
mlflow.MlflowClient().transition_model_version_stage(
    name="LoanPrediction",
    version=2,
    stage="Production"  # None -> Staging -> Production -> Archived
)
```

---

## Phase 4: Containerization & Deployment

### Docker Build Process

```
+-----------------------------------------------------------------------------+
|                         DOCKER BUILD PROCESS                                 |
+-----------------------------------------------------------------------------+
|                                                                              |
|   Dockerfile                                                                 |
|   +-----------------------------------------------------------------------+  |
|   |  FROM python:3.11-slim                                                |  |
|   |       |                                                               |  |
|   |       v                                                               |  |
|   |  Install System Dependencies (AWS CLI, libs)                          |  |
|   |       |                                                               |  |
|   |       v                                                               |  |
|   |  COPY requirements.txt -> pip install                                 |  |
|   |       |                                                               |  |
|   |       v                                                               |  |
|   |  COPY main.py, prediction_model/                                      |  |
|   |       |                                                               |  |
|   |       v                                                               |  |
|   |  Create start.sh (S3 sync + uvicorn)                                  |  |
|   |       |                                                               |  |
|   |       v                                                               |  |
|   |  EXPOSE 8005 + HEALTHCHECK                                            |  |
|   +-----------------------------------------------------------------------+  |
|                              |                                               |
|                              v                                               |
|   +-----------------------------------------------------------------------+  |
|   |                    AWS ECR Repository                                 |  |
|   |         513348493761.dkr.ecr.eu-west-2.amazonaws.com/mlops/loan_pred  |  |
|   +-----------------------------------------------------------------------+  |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### Kubernetes Deployment Architecture

```
+-----------------------------------------------------------------------------+
|                      KUBERNETES DEPLOYMENT (EKS)                             |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Namespace: loan-prediction-mlops                                            |
|  +-------------------------------------------------------------------------+ |
|  |                                                                          | |
|  |  +-------------------------------------------------------------------+   | |
|  |  |                        Service (LoadBalancer)                     |   | |
|  |  |                         Port: 80 -> 8005                          |   | |
|  |  +-------------------------------+-----------------------------------+   | |
|  |                                  |                                       | |
|  |                    +-------------+-------------+                         | |
|  |                    |             |             |                         | |
|  |                    v             v             v                         | |
|  |  +------------------+ +------------------+ +------------------+          | |
|  |  |   Pod (Replica 1)| |   Pod (Replica 2)| |   Pod (Replica 3)|          | |
|  |  |  +------------+  | |  +------------+  | |  +------------+  |          | |
|  |  |  | Container  |  | |  | Container  |  | |  | Container  |  |          | |
|  |  |  | loan-pred  |  | |  | loan-pred  |  | |  | loan-pred  |  |          | |
|  |  |  |            |  | |  |            |  | |  |            |  |          | |
|  |  |  | Port: 8005 |  | |  | Port: 8005 |  | |  | Port: 8005 |  |          | |
|  |  |  +------------+  | |  +------------+  | |  +------------+  |          | |
|  |  |                  | |                  | |                  |          | |
|  |  |  Probes:         | |  Probes:         | |  Probes:         |          | |
|  |  |  - Liveness      | |  - Liveness      | |  - Liveness      |          | |
|  |  |  - Readiness     | |  - Readiness     | |  - Readiness     |          | |
|  |  +------------------+ +------------------+ +------------------+          | |
|  |                                                                          | |
|  |  Rolling Update Strategy:                                                | |
|  |  - maxSurge: 1 (Allow 1 additional Pod)                                  | |
|  |  - maxUnavailable: 0 (Always maintain 3 available)                       | |
|  |                                                                          | |
|  +-------------------------------------------------------------------------+ |
|                                                                              |
|  ServiceAccount: loan-prediction-sa                                          |
|  +-- IRSA: arn:aws:iam::078607863580:role/loan-prediction-s3-access         |
|                                                                              |
+-----------------------------------------------------------------------------+
```

---

## Phase 5: API Service Layer

### FastAPI Service Layer

```
+-----------------------------------------------------------------------------+
|                           FASTAPI SERVICE LAYER                              |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Application Startup:                                                        |
|  +-------------------------------------------------------------------------+ |
|  |  1. start.sh executes                                                    | |
|  |       |                                                                  | |
|  |       v                                                                  | |
|  |  2. aws s3 sync (Download mlruns from S3)                                | |
|  |       |                                                                  | |
|  |       v                                                                  | |
|  |  3. Load MLflow Model Registry                                           | |
|  |       |                                                                  | |
|  |       v                                                                  | |
|  |  4. Initialize FastAPI + Prometheus Instrumentator                       | |
|  |       |                                                                  | |
|  |       v                                                                  | |
|  |  5. uvicorn server starts on port 8005                                   | |
|  +-------------------------------------------------------------------------+ |
|                                                                              |
+-----------------------------------------------------------------------------+
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API Documentation & Endpoints List |
| `/health` | GET | Health Check (for K8s probes) |
| `/metrics` | GET | Prometheus Metrics |
| `/model_info` | GET | Current Model Information |
| `/list_models` | GET | All Registered Model Versions |
| `/prediction_api` | POST | Single Loan Prediction |
| `/batch_prediction` | POST | Batch CSV File Prediction |

### Single Prediction Request Body (Pydantic Validated)

```json
{
  "Gender": "Male",
  "Married": "Yes",
  "Dependents": "1",
  "Education": "Graduate",
  "Self_Employed": "No",
  "ApplicantIncome": 5000,
  "CoapplicantIncome": 2000,
  "LoanAmount": 150,
  "Loan_Amount_Term": 360,
  "Credit_History": 1,
  "Property_Area": "Urban"
}
```

### Prediction Flow

```
Request -> Pydantic Validation -> DataFrame Conversion -> Pipeline Transform -> Model Predict -> Response
```

---

## Phase 6: Monitoring Infrastructure

### Monitoring Architecture

```
+-----------------------------------------------------------------------------+
|                        MONITORING ARCHITECTURE                               |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +-------------------------------------------------------------------------+ |
|  |                     Prometheus Metrics Collection                        | |
|  |                                                                          | |
|  |  FastAPI App ----> prometheus_fastapi_instrumentator                     | |
|  |       |                                                                  | |
|  |       v                                                                  | |
|  |  /metrics endpoint exposes:                                              | |
|  |  +-------------------------------------------------------------------+   | |
|  |  | - http_requests_total{method, endpoint, status}                   |   | |
|  |  | - http_request_duration_seconds{method, endpoint}                 |   | |
|  |  | - http_requests_in_progress                                       |   | |
|  |  | - python_info                                                     |   | |
|  |  | - process_cpu_seconds_total                                       |   | |
|  |  | - process_resident_memory_bytes                                   |   | |
|  |  +-------------------------------------------------------------------+   | |
|  |                                                                          | |
|  +-------------------------------------------------------------------------+ |
|                              |                                               |
|                              v                                               |
|  +-------------------------------------------------------------------------+ |
|  |                        Prometheus Server                                 | |
|  |  +-------------------------------------------------------------------+   | |
|  |  | scrape_configs:                                                   |   | |
|  |  |   - job_name: 'loan-prediction'                                   |   | |
|  |  |     kubernetes_sd_configs:                                        |   | |
|  |  |       annotations:                                                |   | |
|  |  |         prometheus.io/scrape: "true"                              |   | |
|  |  |         prometheus.io/port: "8005"                                |   | |
|  |  |         prometheus.io/path: "/metrics"                            |   | |
|  |  +-------------------------------------------------------------------+   | |
|  +-------------------------------------------------------------------------+ |
|                              |                                               |
|                              v                                               |
|  +-------------------------------------------------------------------------+ |
|  |                       Grafana Dashboards                                 | |
|  |  +---------------+  +---------------+  +---------------+                 | |
|  |  | Request Rate  |  | Latency P95   |  | Error Rate    |                 | |
|  |  | 150 req/min   |  | 45ms          |  | 0.1%          |                 | |
|  |  +---------------+  +---------------+  +---------------+                 | |
|  |  +---------------+  +---------------+  +---------------+                 | |
|  |  | CPU Usage     |  | Memory Usage  |  | Pod Status    |                 | |
|  |  | 25%           |  | 512MB/1GB     |  | 3/3 Healthy   |                 | |
|  |  +---------------+  +---------------+  +---------------+                 | |
|  +-------------------------------------------------------------------------+ |
|                                                                              |
+-----------------------------------------------------------------------------+
```

---

## Phase 7: Data Drift Detection

### Evidently Drift Monitoring

```
+-----------------------------------------------------------------------------+
|                     EVIDENTLY DRIFT MONITORING                               |
+-----------------------------------------------------------------------------+
|                                                                              |
|  +-------------------------------------------------------------------------+ |
|  |                        Drift Detection Flow                              | |
|  |                                                                          | |
|  |   Training Data              Production Data                             | |
|  |   (Reference)                (Current)                                   | |
|  |   +----------+               +----------+                                | |
|  |   |train.csv |               | API Logs |                                | |
|  |   |          |               | /predict |                                | |
|  |   +----+-----+               +----+-----+                                | |
|  |        |                          |                                      | |
|  |        +----------+---------------+                                      | |
|  |                   |                                                      | |
|  |                   v                                                      | |
|  |   +-------------------------------------------------------------------+  | |
|  |   |              Evidently Data Drift Report                          |  | |
|  |   |  +---------------------------------------------------------+     |  | |
|  |   |  | Feature Drift Analysis:                                  |     |  | |
|  |   |  |                                                          |     |  | |
|  |   |  | ApplicantIncome:  ######....  Drift: 0.15 (No drift)     |     |  | |
|  |   |  | LoanAmount:       #####.....  Drift: 0.12 (No drift)     |     |  | |
|  |   |  | Credit_History:   ##........  Drift: 0.05 (No drift)     |     |  | |
|  |   |  | Property_Area:    ########..  Drift: 0.35 (DRIFT!)       |     |  | |
|  |   |  |                                                          |     |  | |
|  |   |  | Overall Dataset Drift: DETECTED                          |     |  | |
|  |   |  +---------------------------------------------------------+     |  | |
|  |   +-------------------------------------------------------------------+  | |
|  |                   |                                                      | |
|  |                   v                                                      | |
|  |   +-------------------------------------------------------------------+  | |
|  |   |                    Alert & Actions                                |  | |
|  |   |  - Upload report to S3                                            |  | |
|  |   |  - Trigger retraining pipeline (optional)                         |  | |
|  |   |  - Send notification to team                                      |  | |
|  |   +-------------------------------------------------------------------+  | |
|  |                                                                          | |
|  +-------------------------------------------------------------------------+ |
|                                                                              |
+-----------------------------------------------------------------------------+
```

---

## Complete CI/CD Pipeline

### GitHub Actions Pipeline

```
+-----------------------------------------------------------------------------+
|                         CI/CD PIPELINE (GitHub Actions)                      |
+-----------------------------------------------------------------------------+
|                                                                              |
|  Git Push                                                                    |
|      |                                                                       |
|      v                                                                       |
|  +-------------------------------------------------------------------------+ |
|  | Stage 1: Test & Validate                                                 | |
|  | +-------------+  +-------------+  +-------------+                        | |
|  | | pytest      |  | Quality     |  | Security    |                        | |
|  | | Unit Tests  |  | Gates       |  | Scan        |                        | |
|  | |             |  | (F1 > 0.85) |  |             |                        | |
|  | +-------------+  +-------------+  +-------------+                        | |
|  +-------------------------------------------------------------------------+ |
|      |                                                                       |
|      v                                                                       |
|  +-------------------------------------------------------------------------+ |
|  | Stage 2: Build & Push                                                    | |
|  | +-------------+  +-------------+  +-------------+                        | |
|  | | Docker      |  | ECR Login   |  | Push Image  |                        | |
|  | | Build       |--->|             |--->| :latest     |                        | |
|  | |             |  |             |  | :v1.0.0     |                        | |
|  | +-------------+  +-------------+  +-------------+                        | |
|  +-------------------------------------------------------------------------+ |
|      |                                                                       |
|      v                                                                       |
|  +-------------------------------------------------------------------------+ |
|  | Stage 3: Deploy                                                          | |
|  | +-------------+  +-------------+  +-------------+                        | |
|  | | kubectl     |  | Rolling     |  | Health      |                        | |
|  | | apply       |--->| Update      |--->| Verify      |                        | |
|  | |             |  |             |  |             |                        | |
|  | +-------------+  +-------------+  +-------------+                        | |
|  +-------------------------------------------------------------------------+ |
|      |                                                                       |
|      v                                                                       |
|  +-------------------------------------------------------------------------+ |
|  | Stage 4: Post-Deploy                                                     | |
|  | +-------------+  +-------------+  +-------------+                        | |
|  | | Smoke Tests |  | Monitor     |  | Rollback    |                        | |
|  | |             |  | Metrics     |  | (if needed) |                        | |
|  | |             |  |             |  |             |                        | |
|  | +-------------+  +-------------+  +-------------+                        | |
|  +-------------------------------------------------------------------------+ |
|                                                                              |
+-----------------------------------------------------------------------------+
```

---

## Project Directory Structure

```
Loan-Prediction_MLOps/
|-- datasets/                       # Datasets (DVC tracked)
|   |-- train.csv
|   +-- test.csv
|-- prediction_model/               # Core ML Package
|   |-- config/
|   |   +-- config.py               # Configuration (S3, MLflow, Features)
|   |-- processing/
|   |   +-- preprocessing.py        # Data preprocessing transformers
|   +-- training_pipeline.py        # Model training main program
|-- drift_monitoring/               # Evidently drift monitoring
|   +-- config.py
|-- k8s/                            # Kubernetes deployment configuration
|   |-- namespace.yml
|   |-- deployment.yml              # 3 replicas + Rolling Update
|   |-- services.yml                # LoadBalancer
|   +-- serviceaccount.yml          # IRSA for AWS access
|-- tests/                          # Test suite
|   |-- conftest.py
|   +-- test_api.py
|-- mlruns/                         # MLflow experiment tracking (auto-generated)
|-- .dvc/                           # DVC configuration
|   +-- config                      # S3 remote configuration
|-- main.py                         # FastAPI application entry point
|-- Dockerfile                      # Container configuration
|-- requirements.txt                # Python dependencies
|-- setup.py                        # Package installation configuration
|-- .env                            # Environment variables
+-- datasets.dvc                    # DVC data tracking file
```
