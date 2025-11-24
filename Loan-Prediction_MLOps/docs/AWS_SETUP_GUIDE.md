# AWS Infrastructure Setup Guide

## Overview

This guide explains how to configure AWS resources for the MLOps pipeline.

## 1. GitHub Actions OIDC Setup

### Create OIDC Identity Provider

1. Go to AWS IAM Console > Identity Providers > Add Provider
2. Configure:
   - Provider Type: OpenID Connect
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`
3. Click "Add provider"

**AWS CLI Command**:
```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### Create IAM Role for GitHub Actions

1. Create a new IAM Role
2. Select "Web identity" as trusted entity
3. Choose the OIDC provider created above
4. Audience: `sts.amazonaws.com`
5. Add permissions policies (see below)
6. Role name: `github-actions-mlops-role`

**Trust Policy** (edit after creation):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:AD2000X/Loan-Prediction_MLOps:*"
        }
      }
    }
  ]
}
```

**Replace**:
- `YOUR_ACCOUNT_ID` with your AWS account ID
- `AD2000X/Loan-Prediction_MLOps` with your GitHub repo

### Required IAM Permissions

Attach these policies to the role:

**1. S3 Access Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::loanpred-mlops-20251118-120330",
        "arn:aws:s3:::loanpred-mlops-20251118-120330/*"
      ]
    }
  ]
}
```

**2. ECR Access Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    }
  ]
}
```

**3. EKS Access Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters"
      ],
      "Resource": "arn:aws:eks:eu-west-2:YOUR_ACCOUNT_ID:cluster/loan-pred-cluster"
    }
  ]
}
```

## 2. Configure GitHub Secrets

Go to GitHub Repository > Settings > Secrets and variables > Actions

Add these secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `AWS_REGION` | AWS region | `eu-west-2` |
| `EKS_CLUSTER_NAME` | EKS cluster name | `loan-pred-cluster` |
| `ACTIONS_GITHUB_ROLE_ARN` | IAM role ARN | `arn:aws:iam::339713054990:role/github-actions-mlops-role` |
| `AWS_ACCOUNT_ID` | AWS account ID | `339713054990` |

**To get your Role ARN**:
```bash
aws iam get-role --role-name github-actions-mlops-role --query 'Role.Arn' --output text
```

## 3. Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://loanpred-mlops-20251118-120330 --region eu-west-2

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket loanpred-mlops-20251118-120330 \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket loanpred-mlops-20251118-120330 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket loanpred-mlops-20251118-120330 \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

## 4. Create ECR Repository

```bash
# Create repository
aws ecr create-repository \
  --repository-name mlops/loan_pred \
  --region eu-west-2

# Get repository URI
aws ecr describe-repositories \
  --repository-names mlops/loan_pred \
  --query 'repositories[0].repositoryUri' \
  --output text
```

## 5. Create EKS Cluster (if not exists)

```bash
# Install eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Create cluster
eksctl create cluster \
  --name loan-pred-cluster \
  --region eu-west-2 \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed
```

## 6. Configure EKS for S3 Access

### Create IAM OIDC Provider for EKS

```bash
eksctl utils associate-iam-oidc-provider \
  --cluster loan-pred-cluster \
  --region eu-west-2 \
  --approve
```

### Create IAM Service Account

```bash
# Create service account with S3 access
eksctl create iamserviceaccount \
  --name loan-prediction-sa \
  --namespace loan-prediction-mlops \
  --cluster loan-pred-cluster \
  --region eu-west-2 \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve
```

**Or create custom policy**:

1. Create policy file `s3-read-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::loanpred-mlops-20251118-120330",
        "arn:aws:s3:::loanpred-mlops-20251118-120330/*"
      ]
    }
  ]
}
```

2. Create and attach policy:
```bash
# Create policy
aws iam create-policy \
  --policy-name MLflowS3ReadPolicy \
  --policy-document file://s3-read-policy.json

# Attach to service account
eksctl create iamserviceaccount \
  --name loan-prediction-sa \
  --namespace loan-prediction-mlops \
  --cluster loan-pred-cluster \
  --region eu-west-2 \
  --attach-policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/MLflowS3ReadPolicy \
  --approve
```

## 7. Verification

### Test GitHub Actions OIDC

```bash
# Check OIDC provider
aws iam list-open-id-connect-providers

# Check role
aws iam get-role --role-name github-actions-mlops-role

# Check role policies
aws iam list-attached-role-policies --role-name github-actions-mlops-role
```

### Test S3 Access

```bash
# Upload test file
echo "test" > test.txt
aws s3 cp test.txt s3://loanpred-mlops-20251118-120330/test.txt

# List bucket
aws s3 ls s3://loanpred-mlops-20251118-120330/

# Download test file
aws s3 cp s3://loanpred-mlops-20251118-120330/test.txt downloaded.txt
```

### Test ECR Access

```bash
# Login to ECR
aws ecr get-login-password --region eu-west-2 | \
  docker login --username AWS --password-stdin \
  339713054990.dkr.ecr.eu-west-2.amazonaws.com

# Push test image
docker pull alpine:latest
docker tag alpine:latest 339713054990.dkr.ecr.eu-west-2.amazonaws.com/mlops/loan_pred:test
docker push 339713054990.dkr.ecr.eu-west-2.amazonaws.com/mlops/loan_pred:test
```

### Test EKS Access

```bash
# Update kubeconfig
aws eks update-kubeconfig --name loan-pred-cluster --region eu-west-2

# Test access
kubectl get nodes
kubectl get namespaces
```

## 8. Quick Setup Script

```bash
#!/bin/bash
# AWS MLOps Infrastructure Setup

set -e

AWS_REGION="eu-west-2"
CLUSTER_NAME="loan-pred-cluster"
BUCKET_NAME="loanpred-mlops-20251118-120330"
ECR_REPO="mlops/loan_pred"
GITHUB_REPO="AD2000X/Loan-Prediction_MLOps"

echo "Setting up AWS infrastructure for MLOps..."

# 1. Create OIDC provider for GitHub Actions
echo "Creating GitHub OIDC provider..."
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 || echo "Provider already exists"

# 2. Create S3 bucket
echo "Creating S3 bucket..."
aws s3 mb s3://$BUCKET_NAME --region $AWS_REGION || echo "Bucket exists"
aws s3api put-bucket-versioning --bucket $BUCKET_NAME --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket $BUCKET_NAME --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# 3. Create ECR repository
echo "Creating ECR repository..."
aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION || echo "Repository exists"

# 4. Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $ACCOUNT_ID"

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create IAM role 'github-actions-mlops-role' with trust policy (see docs)"
echo "2. Add GitHub secrets:"
echo "   - AWS_REGION: $AWS_REGION"
echo "   - EKS_CLUSTER_NAME: $CLUSTER_NAME"
echo "   - ACTIONS_GITHUB_ROLE_ARN: arn:aws:iam::$ACCOUNT_ID:role/github-actions-mlops-role"
echo "   - AWS_ACCOUNT_ID: $ACCOUNT_ID"
```

## Common Issues

### Issue: "Request ARN is invalid"

**Solution**:
1. Check `ACTIONS_GITHUB_ROLE_ARN` secret is set correctly
2. Format: `arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME`
3. Verify role exists: `aws iam get-role --role-name github-actions-mlops-role`

### Issue: "Access Denied" in GitHub Actions

**Solution**:
1. Check IAM role permissions
2. Verify trust policy allows GitHub repo
3. Ensure OIDC provider is created

### Issue: Pods can't access S3

**Solution**:
1. Check service account annotation: `kubectl describe sa loan-prediction-sa -n loan-prediction-mlops`
2. Verify IAM role for service account exists
3. Check pod environment: `kubectl exec -it <pod> -- env | grep AWS`

## Cost Estimate

- **S3**: < $0.03/month (~100 MB)
- **ECR**: ~$0.10/month (~1 GB images)
- **EKS**: ~$72/month (cluster) + ~$30/month (2 t3.medium nodes)
- **Total**: ~$102/month

Use AWS Free Tier where applicable to reduce costs.

## References

- GitHub OIDC: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
- EKS IAM Roles: https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html
- ECR Documentation: https://docs.aws.amazon.com/ecr/
- S3 Best Practices: https://docs.aws.amazon.com/AmazonS3/latest/userguide/best-practices.html
