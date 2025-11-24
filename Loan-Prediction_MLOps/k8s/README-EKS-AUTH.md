# EKS Authentication Setup

This document describes how to configure authentication for the EKS cluster to allow GitHub Actions and other services to access it.

## Background

Modern EKS clusters (created after April 2024) may use Access Entries instead of automatically generating the `aws-auth` ConfigMap. If your cluster doesn't have an `aws-auth` ConfigMap, you need to create it manually to grant access to IAM roles.

## Required IAM Roles

1. **Node IAM Role**: `arn:aws:iam::513348493761:role/EKSNodeRole`
   - Required for EC2 nodes to join the cluster
   - Grants system:nodes permissions

2. **GitHub Actions Role**: `arn:aws:iam::513348493761:role/GitHubActionsRole`
   - Required for CI/CD pipeline to deploy applications
   - Grants system:masters (admin) permissions

## Setup Instructions

### Method 1: Manual Setup (One-time)

1. Connect to your EKS cluster:
```bash
aws eks update-kubeconfig --region eu-west-2 --name YOUR_CLUSTER_NAME
```

2. Check if aws-auth ConfigMap exists:
```bash
kubectl get configmap aws-auth -n kube-system
```

3. If it doesn't exist or needs updating, apply the configuration:
```bash
kubectl apply -f k8s/aws-auth.yaml
```

4. Verify the configuration:
```bash
kubectl get configmap aws-auth -n kube-system -o yaml
```

### Method 2: Using the Setup Script

Run the provided script:
```bash
./scripts/setup-eks-auth.sh YOUR_CLUSTER_NAME eu-west-2
```

### Method 3: Automatic Setup in CI/CD

The GitHub Actions workflows (`cicd.yml` and `cicd-v2.yml`) now automatically configure the aws-auth ConfigMap during deployment:

1. The workflow checks if aws-auth exists
2. If not found, it creates it automatically
3. If it exists, it updates the configuration
4. Verifies cluster access before proceeding

## Troubleshooting

### Error: "the server has asked for the client to provide credentials"
This means the IAM role doesn't have access to the cluster. Apply the aws-auth ConfigMap as described above.

### Error: "No cluster found for name"
Ensure you're using the correct cluster name and region.

### Error: "Unauthorized"
The IAM role is recognized but doesn't have the necessary permissions. Check that the role ARN in aws-auth.yaml is correct.

## Security Notes

- The GitHub Actions role is granted `system:masters` permissions for full cluster access
- In production, consider using more restricted RBAC roles instead of system:masters
- Regularly audit the aws-auth ConfigMap to ensure only authorized roles have access

## Files

- `k8s/aws-auth.yaml`: ConfigMap defining IAM role mappings
- `scripts/setup-eks-auth.sh`: Bash script for automated setup
- `.github/workflows/cicd.yml`: CI/CD pipeline with automatic auth configuration