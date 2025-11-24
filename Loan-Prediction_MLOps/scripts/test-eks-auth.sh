#!/bin/bash

# Test script to verify EKS authentication is working

set -e

echo "========================================="
echo "EKS Authentication Test"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ kubectl installed${NC}"

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ AWS CLI installed${NC}"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}✗ AWS credentials not configured${NC}"
    exit 1
fi

IDENTITY=$(aws sts get-caller-identity --query 'Arn' --output text)
echo -e "${GREEN}✓ AWS identity: $IDENTITY${NC}"

# Check cluster connectivity
echo ""
echo "Testing cluster access..."

if kubectl get nodes &> /dev/null; then
    echo -e "${GREEN}✓ Can list nodes${NC}"
    kubectl get nodes
else
    echo -e "${RED}✗ Cannot list nodes - authentication may be failing${NC}"
    exit 1
fi

# Check aws-auth ConfigMap
echo ""
echo "Checking aws-auth ConfigMap..."

if kubectl get configmap aws-auth -n kube-system &> /dev/null; then
    echo -e "${GREEN}✓ aws-auth ConfigMap exists${NC}"

    # Check if GitHub Actions role is configured
    if kubectl get configmap aws-auth -n kube-system -o yaml | grep -q "GitHubActionsRole"; then
        echo -e "${GREEN}✓ GitHubActionsRole is configured${NC}"
    else
        echo -e "${YELLOW}⚠ GitHubActionsRole not found in aws-auth${NC}"
    fi

    # Check if Node role is configured
    if kubectl get configmap aws-auth -n kube-system -o yaml | grep -q "EKSNodeRole"; then
        echo -e "${GREEN}✓ EKSNodeRole is configured${NC}"
    else
        echo -e "${YELLOW}⚠ EKSNodeRole not found in aws-auth${NC}"
    fi
else
    echo -e "${RED}✗ aws-auth ConfigMap not found${NC}"
    echo "  Run: kubectl apply -f k8s/aws-auth.yaml"
    exit 1
fi

# Test namespace operations
echo ""
echo "Testing namespace operations..."

if kubectl get namespaces &> /dev/null; then
    echo -e "${GREEN}✓ Can list namespaces${NC}"

    # Check if loan-prediction-mlops namespace exists
    if kubectl get namespace loan-prediction-mlops &> /dev/null; then
        echo -e "${GREEN}✓ loan-prediction-mlops namespace exists${NC}"
    else
        echo -e "${YELLOW}⚠ loan-prediction-mlops namespace not found${NC}"
        echo "  Will be created during deployment"
    fi
else
    echo -e "${RED}✗ Cannot list namespaces${NC}"
    exit 1
fi

# Test permissions
echo ""
echo "Testing permissions..."

if kubectl auth can-i create pods --all-namespaces &> /dev/null; then
    echo -e "${GREEN}✓ Can create pods${NC}"
else
    echo -e "${YELLOW}⚠ Cannot create pods (may need elevated permissions)${NC}"
fi

if kubectl auth can-i create deployments --all-namespaces &> /dev/null; then
    echo -e "${GREEN}✓ Can create deployments${NC}"
else
    echo -e "${YELLOW}⚠ Cannot create deployments (may need elevated permissions)${NC}"
fi

echo ""
echo "========================================="
echo -e "${GREEN}EKS Authentication Test Complete${NC}"
echo "========================================="