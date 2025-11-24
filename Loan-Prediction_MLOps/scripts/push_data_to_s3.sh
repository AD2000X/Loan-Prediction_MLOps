#!/bin/bash

# Script to push datasets to S3 via DVC
# Usage: ./scripts/push_data_to_s3.sh

set -e  # Exit on error

echo "========================================"
echo "DVC Data Push to S3"
echo "========================================"

# Check if DVC is installed
if ! command -v dvc &> /dev/null; then
    echo "Error: DVC is not installed"
    echo "Install with: pip install dvc[s3]"
    exit 1
fi

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

echo "AWS Identity:"
aws sts get-caller-identity

# Check if datasets directory exists
if [ ! -d "datasets" ]; then
    echo "Error: datasets/ directory not found"
    exit 1
fi

echo ""
echo "Datasets found:"
ls -lh datasets/

# DVC add (if not already tracked)
echo ""
echo "Tracking datasets with DVC..."
dvc add datasets/

# Show DVC status
echo ""
echo "DVC Status:"
dvc status

# Push to S3
echo ""
echo "Pushing datasets to S3..."
dvc push -v

echo ""
echo "========================================"
echo "Success! Data pushed to S3"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. git add datasets.dvc .gitignore"
echo "2. git commit -m 'Update datasets'"
echo "3. git push"
echo ""
echo "S3 Location: s3://loanpred-mlops-20251118-120330/"
echo "========================================"
