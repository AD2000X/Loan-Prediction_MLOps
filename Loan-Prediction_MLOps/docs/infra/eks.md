# Amazon EKS Infrastructure Documentation

Amazon Elastic Kubernetes Service hosts the loan prediction ML service.

## Cluster Details
- Cluster Name: loan-pred-cluster
- Region: eu-west-2
- Kubernetes Version: 1.28+

## Node Configuration
- Instance Type: t3.medium
- Min Nodes: 2
- Max Nodes: 3
- Autoscaling: Enabled

## Deployment Strategy
- Blue-Green: Zero-downtime deployments
- Canary: Progressive rollout (10% → 100%)
- Replicas: 3 pods per deployment

## Namespace
- Name: loan-prediction-mlops
- Service Account: loan-prediction-sa
- IAM Role: Annotated for S3 access

## Monitoring
Integrated with Prometheus and Grafana for metrics collection.
