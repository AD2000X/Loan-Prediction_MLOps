# Amazon ECR Infrastructure Documentation

Amazon Elastic Container Registry stores Docker images for the loan prediction service.

## Repository Details
- Repository: mlops/loan_pred
- Region: eu-west-2
- Registry: 339713054990.dkr.ecr.eu-west-2.amazonaws.com

## Image Tagging Strategy
- SHA tags: ${github.sha} for traceability
- latest: Always points to most recent build
- stable: Production-tested version

## Image Configuration
- Base: python:3.11-slim
- Size: ~600 MB (S3-based model loading)
- Environment: MLFLOW_TRACKING_URI, MODEL_STAGE

## CI/CD Integration
Images automatically built and pushed during GitHub Actions workflow.
