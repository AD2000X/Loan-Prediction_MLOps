#!/bin/bash

# Script to configure aws-auth ConfigMap for EKS cluster
# This grants access to GitHub Actions role and EKS node role

set -e

echo "========================================="
echo "Setting up EKS Authentication"
echo "========================================="

# Check if cluster name is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <cluster-name> [region]"
    echo "Example: $0 my-eks-cluster eu-west-2"
    exit 1
fi

CLUSTER_NAME=$1
AWS_REGION=${2:-eu-west-2}

echo "Cluster: $CLUSTER_NAME"
echo "Region: $AWS_REGION"

# Update kubeconfig
echo "Configuring kubectl..."
aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME

# Check current aws-auth status
echo ""
echo "Checking current aws-auth ConfigMap..."
kubectl get configmap aws-auth -n kube-system 2>/dev/null || echo "aws-auth ConfigMap not found"

# Apply the aws-auth ConfigMap
echo ""
echo "Applying aws-auth ConfigMap..."
kubectl apply -f k8s/aws-auth.yaml

# Verify the ConfigMap was created
echo ""
echo "Verifying aws-auth ConfigMap..."
kubectl get configmap aws-auth -n kube-system

echo ""
echo "========================================="
echo "EKS Authentication setup complete!"
echo "========================================="

# Test authentication
echo ""
echo "Testing cluster access..."
kubectl get nodes

echo ""
echo "GitHub Actions role and Node role have been granted access to the cluster"