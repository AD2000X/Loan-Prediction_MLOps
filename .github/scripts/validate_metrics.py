#!/usr/bin/env python3
"""
Validate model metrics from MLflow
"""
import mlflow
import os
import json
import sys

def main():
    # Set MLflow tracking URI to local mlruns directory
    # Use GITHUB_WORKSPACE if available, otherwise use default path
    workspace = os.getenv("GITHUB_WORKSPACE", "/home/runner/work/Loan-Prediction_MLOps/Loan-Prediction_MLOps")
    tracking_uri = f"file://{workspace}/mlruns"
    print(f"Using MLflow tracking URI: {tracking_uri}")
    mlflow.set_tracking_uri(tracking_uri)

    client = mlflow.tracking.MlflowClient()

    # Get latest production model
    versions = client.get_latest_versions('LoanPrediction', stages=['Production'])
    if not versions:
        print('No production model found')
        sys.exit(1)

    version = versions[0]
    run = mlflow.get_run(version.run_id)

    # Extract metrics
    metrics = {
        'f1_score': run.data.metrics.get('f1_score', 0),
        'accuracy': run.data.metrics.get('accuracy', 0),
        'recall': run.data.metrics.get('recall', 0),
        'precision': run.data.metrics.get('precision', 0)
    }

    # Print metrics
    print('Model Metrics:')
    print(f"  F1 Score: {metrics['f1_score']:.4f}")
    print(f"  Accuracy: {metrics['accuracy']:.4f}")
    print(f"  Recall: {metrics['recall']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")

    # Save to GitHub output
    github_output = os.getenv('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"f1_score={metrics['f1_score']}\n")
            f.write(f"accuracy={metrics['accuracy']}\n")
            f.write(f"recall={metrics['recall']}\n")

    # Save metrics to file for artifact
    with open('model_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

if __name__ == '__main__':
    main()
