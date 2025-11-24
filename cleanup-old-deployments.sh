#!/bin/bash
# Cleanup script for old blue-green deployments
# This script removes the old blue-green deployments that are no longer needed
# after migrating to rolling update deployment

echo "Cleaning up old blue-green deployments..."

# Delete old blue deployment
echo "Deleting loan-prediction-blue deployment..."
kubectl delete deployment loan-prediction-blue -n loan-prediction-mlops --ignore-not-found=true

# Delete old green deployment
echo "Deleting loan-prediction-green deployment..."
kubectl delete deployment loan-prediction-green -n loan-prediction-mlops --ignore-not-found=true

# Delete internal blue service
echo "Deleting loan-prediction-blue-internal service..."
kubectl delete service loan-prediction-blue-internal -n loan-prediction-mlops --ignore-not-found=true

# Delete internal green service
echo "Deleting loan-prediction-green-internal service..."
kubectl delete service loan-prediction-green-internal -n loan-prediction-mlops --ignore-not-found=true

# Delete evicted pods
echo "Cleaning up evicted pods..."
kubectl delete pods -n loan-prediction-mlops --field-selector=status.phase=Failed

echo "Cleanup complete!"
echo ""
echo "Current pods:"
kubectl get pods -n loan-prediction-mlops

echo ""
echo "Current deployments:"
kubectl get deployments -n loan-prediction-mlops

echo ""
echo "Current services:"
kubectl get services -n loan-prediction-mlops
