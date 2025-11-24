# Quick Start: DVC + CI/CD Workflow

## New Features Added

Your MLOps pipeline now includes:
- **DVC Data Version Control** - Datasets tracked in S3
- **Automated Training in CI/CD** - Models train on every push
- **MLflow Artifact Storage** - Results synced to S3
- **Complete Reproducibility** - Full data + code versioning

---

## Prerequisites

1. **AWS Credentials Configured**
   ```bash
   aws configure
   # Use your AWS credentials with S3 access
   ```

2. **DVC Installed**
   ```bash
   pip install dvc[s3]
   ```

3. **Git Repository Access**
   - Push access to the repository
   - GitHub Actions enabled

---

## Quick Start (3 Steps)

### Step 1: Push Current Datasets to S3

**Windows:**
```cmd
scripts\push_data_to_s3.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/push_data_to_s3.sh
./scripts/push_data_to_s3.sh
```

**Manual:**
```bash
# Track datasets
dvc add datasets/

# Push to S3
dvc push

# Commit changes
git add datasets.dvc .gitignore
git commit -m "Add datasets to DVC"
git push
```

### Step 2: Trigger CI/CD Pipeline

```bash
# Any push to main/develop triggers full pipeline
git push origin develop
```

The pipeline will:
1. Pull data from S3
2. Train models
3. Push artifacts to S3
4. Build and deploy Docker image

### Step 3: Monitor Progress

**GitHub Actions:**
- Go to Actions tab in GitHub
- Watch the workflow progress
- View logs for each step

**Local Verification:**
```bash
# Pull trained models from S3
aws s3 sync s3://loanpred-mlops-20251118-120330/mlruns/ ./mlruns/

# View MLflow UI
mlflow ui --backend-store-uri ./mlruns
```

---

## Complete Workflow

### For Data Scientists

**Update Training Data:**
```bash
# 1. Add new data
cp new_data.csv datasets/

# 2. Track with DVC
dvc add datasets/

# 3. Push to S3
dvc push

# 4. Commit and push
git add datasets.dvc
git commit -m "Update training data"
git push

# CI/CD automatically retrains with new data
```

### For ML Engineers

**Deploy New Model:**
```bash
# 1. Update model code
vim prediction_model/training_pipeline.py

# 2. Commit and push
git add -A
git commit -m "Improve model architecture"
git push

# CI/CD trains, tests, and deploys automatically
```

### For DevOps

**Monitor Pipeline:**
```bash
# Check S3 storage
aws s3 ls s3://loanpred-mlops-20251118-120330/ --recursive --summarize

# Check EKS deployment
kubectl get pods -n loan-prediction-mlops

# View metrics
kubectl port-forward -n loan-prediction-mlops svc/loan-prediction-service 8005:8005
```

---

## Verification Checklist

### After Setup:

- [ ] Datasets uploaded to S3
- [ ] DVC tracking configured
- [ ] CI/CD pipeline runs successfully
- [ ] Models trained and stored in S3
- [ ] Docker image built and pushed to ECR
- [ ] EKS deployment updated

### Test Commands:

```bash
# Verify DVC
dvc status
dvc remote list

# Verify S3
aws s3 ls s3://loanpred-mlops-20251118-120330/

# Verify MLflow
ls -la mlruns/

# Verify API
curl http://localhost:8005/health
```

---

## Troubleshooting

### Common Issues

**1. DVC Push Fails**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify S3 permissions
aws s3 ls s3://loanpred-mlops-20251118-120330/
```

**2. CI/CD Fails at DVC Pull**
- Check GitHub Actions secrets
- Verify OIDC configuration
- Check S3 bucket policy

**3. Models Not Training**
- Check dataset paths
- Verify Python environment
- Review training logs in GitHub Actions

---

## Architecture Overview

```
Local Development          GitHub Actions            AWS Cloud
      |                         |                        |
   [Code + Data]           [CI/CD Pipeline]         [Storage + Deploy]
      |                         |                        |
   git push     ——————>    Trigger workflow              |
      |                         |                        |
   dvc push     ——————————————————————————————>     S3 Bucket
      |                         |                        |
      |                    dvc pull    <————————————————|
      |                         |                        |
      |                   Train Models                   |
      |                         |                        |
      |                   mlflow sync  ——————————————>   |
      |                         |                        |
      |                  Docker build                    |
      |                         |                        |
      |                   Push to ECR  ——————————————>   |
      |                         |                        |
      |                  Deploy to EKS ——————————————>   |
```

---

## Benefits

1. **Version Control**: Every dataset version is tracked
2. **Reproducibility**: Exact data + code = same results
3. **Collaboration**: Team members share data via S3
4. **Automation**: Push code = automatic retraining
5. **Scalability**: S3 handles any data size

---

## Next Steps

1. **Explore MLflow UI**: View experiments and metrics
2. **Monitor Drift**: Check data drift dashboard
3. **Optimize Pipeline**: Reduce training time
4. **Add More Data**: Expand training dataset
5. **Implement A/B Testing**: Test model variations

---

## Support

- **Documentation**: [DVC Docs](https://dvc.org/doc) | [MLflow Docs](https://mlflow.org/docs)
- **Issues**: GitHub Issues page
- **Team**: Contact ML platform team

---

Last updated: November 2024