# Amazon ECR Infrastructure Documentation

Amazon Elastic Container Registry stores Docker images for the loan prediction service.

## Repository Details
- Repository: mlops/loan_pred
- Region: eu-west-2
- Registry: 513348493761.dkr.ecr.eu-west-2.amazonaws.com (matches k8s manifest)

## Image Tagging Strategy
- SHA tags: ${github.sha} for traceability
- latest: Always points to most recent build

## Image Configuration
- Base: python:3.11-slim
- Size: S3-based model loading (models synced on start)
- Environment: MLFLOW_TRACKING_URI=file:/app/mlruns, MODEL_STAGE, S3_BUCKET

## CI/CD Integration
Images automatically built and pushed during GitHub Actions workflow.
