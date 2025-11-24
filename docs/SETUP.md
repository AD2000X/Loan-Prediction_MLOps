# Setup Guide - Loan Prediction MLOps

Complete environment setup guide to build the MLOps platform from scratch.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development Environment](#local-development-environment)
- [MLflow Configuration](#mlflow-configuration)
- [AWS Configuration](#aws-configuration)
- [GitHub Secrets Configuration](#github-secrets-configuration)
- [Installation Verification](#installation-verification)

---

## Prerequisites

### Required Software

- **Python 3.11+**
  ```bash
  python --version  # Should display Python 3.11.x
  ```

- **Git**
  ```bash
  git --version
  ```

- **Docker & Docker Compose**
  ```bash
  docker --version
  docker-compose --version
  ```

- **AWS CLI** (for deployment)
  ```bash
  aws --version
  ```

- **kubectl** (for EKS deployment)
  ```bash
  kubectl version --client
  ```

### Optional Software

- **DVC** (Data Version Control)
  ```bash
  pip install dvc[s3]
  ```

---

## Local Development Environment

### 1. Clone Project

```bash
git clone https://github.com/your-org/Loan-Prediction_MLOps.git
cd Loan-Prediction_MLOps
```

### 2. Create Virtual Environment

```bash
# Using venv
python -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (includes testing tools)
pip install -r requirements-dev.txt
```

### 4. Configure DVC (Pull Data)

```bash
# Configure DVC remote (S3)
dvc remote add -d s3remote s3://your-bucket-name/datasets

# Pull data
dvc pull
```

**Note**: AWS credentials must be configured first (see below).

---

## MLflow Configuration

MLflow is used for experiment tracking and model registry.

### Local MLflow Server

1. **Start MLflow Server**
   ```bash
   mlflow server \
     --backend-store-uri sqlite:///mlflow.db \
     --default-artifact-root ./mlruns \
     --host 0.0.0.0 \
     --port 5000
   ```

2. **Set Environment Variable**
   ```bash
   export MLFLOW_TRACKING_URI="http://localhost:5000"
   ```

3. **Access MLflow UI**
   - Open browser: http://localhost:5000

### Verify MLflow Connection

```python
import mlflow

print(f"Tracking URI: {mlflow.get_tracking_uri()}")

# Test creating experiment
mlflow.set_experiment("test-experiment")
```

---

## AWS Configuration

### 1. Install AWS CLI

```bash
# Linux/Mac
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify
aws --version
```

### 2. Configure AWS Credentials

```bash
aws configure
```

Enter the following information:
- **AWS Access Key ID**: `AKIAIOSFODNN7EXAMPLE`
- **AWS Secret Access Key**: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
- **Default region**: `eu-west-2`
- **Default output format**: `json`

### 3. Verify AWS Access

```bash
# Verify identity
aws sts get-caller-identity

# Should return similar to:
# {
#     "UserId": "AIDAI...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-name"
# }
```

### 4. Create S3 Bucket

```bash
# Create bucket (name must be globally unique)
aws s3 mb s3://loanpred-mlops-demo-$(date +%s) --region eu-west-2

# Record bucket name
export S3_BUCKET_NAME="loanpred-mlops-demo-1234567890"

# Verify
aws s3 ls s3://$S3_BUCKET_NAME
```

### 5. Create ECR Repository

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name mlops/loan_pred \
  --region eu-west-2

# Record repository URI
export ECR_REPO_URI="123456789012.dkr.ecr.eu-west-2.amazonaws.com/mlops/loan_pred"
```

### 6. Configure EKS Cluster (if using EKS)

```bash
# Configure kubeconfig
aws eks update-kubeconfig \
  --region eu-west-2 \
  --name your-eks-cluster-name

# Verify connection
kubectl get nodes
```

**Note**: EKS cluster must be created beforehand (outside scope of this document).

---

## GitHub Secrets Configuration

For CI/CD GitHub Actions.

### 1. Access GitHub Secrets

1. Open GitHub repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"

### 2. Add AWS Related Secrets

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AWS_REGION` | `eu-west-2` | AWS Region |
| `EKS_CLUSTER_NAME` | `your-cluster-name` | EKS Cluster Name |
| `ACTIONS_GITHUB_ROLE_ARN` | `arn:aws:iam::123456789012:role/GitHubActionsRole` | OIDC Role ARN |

### 3. Add MLflow Related Secrets

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow Tracking URI |

### 4. Configure OIDC (GitHub → AWS)

**Create OIDC Provider**:
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

**Create IAM Role** (`GitHubActionsRole.json`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:your-org/Loan-Prediction_MLOps:*"
        }
      }
    }
  ]
}
```

**Create Role**:
```bash
aws iam create-role \
  --role-name GitHubActionsRole \
  --assume-role-policy-document file://GitHubActionsRole.json

# Attach permission policies
aws iam attach-role-policy \
  --role-name GitHubActionsRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEKSClusterPolicy

aws iam attach-role-policy \
  --role-name GitHubActionsRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
```

---

## Installation Verification

### 1. Verify Python Environment

```bash
python -c "import mlflow, pandas, fastapi, boto3; print('All imports OK')"
```

### 2. Run Unit Tests

```bash
# Run tests that don't require MLflow
pytest tests/ -v -m "not integration"

# Run all tests (requires MLflow configuration)
pytest tests/ -v --run-integration
```

### 3. Run API Locally

```bash
python main.py
```

Access:
- API Documentation: http://localhost:8005/docs
- Health Check: http://localhost:8005/health
- Metrics: http://localhost:8005/metrics

### 4. Test API Endpoints

```bash
# Health check
curl http://localhost:8005/health

# Metrics
curl http://localhost:8005/metrics

# Prediction
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

### 5. Start Monitoring Stack

```bash
cd monitoring
docker-compose up -d

# Verify services are running
docker-compose ps

# Access
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### 6. Train Model (requires MLflow configuration)

```bash
python prediction_model/training_pipeline.py
```

Check MLflow UI to view experiment results.

---

## Environment Variables Summary

Create `.env` file (do not commit to Git):

```bash
# MLflow
export MLFLOW_TRACKING_URI="http://localhost:5000"

# AWS
export AWS_REGION="eu-west-2"
export AWS_DEFAULT_REGION="eu-west-2"
export S3_BUCKET_NAME="loanpred-mlops-demo-1234567890"

# DVC
export DVC_REMOTE="s3://loanpred-mlops-demo-1234567890/datasets"

# API
export MODEL_STAGE="Production"  # or "Staging"
```

Load environment variables:
```bash
source .env
```

---

## Common Issues

### Q: MLflow Connection Failed

**A**: Check the following:
1. Is MLflow Server running?
2. Is `MLFLOW_TRACKING_URI` correct?
3. Is firewall blocking connection?

```bash
# Test connection
curl http://localhost:5000
```

### Q: AWS Credentials Invalid

**A**: Reconfigure credentials:
```bash
aws configure list  # Check current configuration
aws configure       # Reconfigure
```

### Q: Docker Permission Issues (Linux)

**A**: Add user to docker group:
```bash
sudo usermod -aG docker $USER
# Log out and log in again
```

### Q: DVC Pull Failed

**A**: Check S3 permissions:
```bash
aws s3 ls s3://your-bucket-name/datasets/
```

---

## Next Steps

- Read [API Documentation](API.md)
- Read [Monitoring Documentation](MONITORING.md)
- View [Deployment Guide](DEPLOYMENT.md)

---

## Support

Having issues?
- Check [Troubleshooting Guide](TROUBLESHOOTING.md)
- Submit GitHub Issue