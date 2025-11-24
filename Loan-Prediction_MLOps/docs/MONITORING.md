# Monitoring and Metrics Guide

This guide provides step-by-step instructions for accessing MLflow experiments, Prometheus metrics, Grafana dashboards, Fairlearn fairness reports, and ML model metrics.

## Table of Contents
1. [MLflow - Experiment Tracking](#mlflow-experiment-tracking)
2. [Prometheus - Metrics Collection](#prometheus-metrics-collection)
3. [Grafana - Visualization](#grafana-visualization)
4. [Fairlearn - Fairness Metrics](#fairlearn-fairness-metrics)
5. [ML Metrics - Model Performance](#ml-metrics-model-performance)
6. [API Endpoints](#api-endpoints)

---

## MLflow - Experiment Tracking

### Option 1: Local MLflow UI

View MLflow experiments stored locally or in S3.

**Prerequisites:**
```bash
pip install mlflow boto3
```

**Step 1: Configure AWS credentials**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=eu-west-2
```

**Step 2: Start MLflow UI with S3 backend**
```bash
# Using S3 artifact store
mlflow ui --backend-store-uri s3://loanpred-mlops-20251118-120330/mlruns --host 0.0.0.0 --port 5000
```

**Step 3: Access MLflow UI**
Open browser: http://localhost:5000

**What you can see:**
- All training experiments and runs
- Hyperparameter values for each trial
- Model metrics (F1, accuracy, precision, recall)
- SHAP importance plots
- Fairlearn fairness metrics
- Logged models and artifacts

### Option 2: Query MLflow Programmatically

**Python script to view experiments:**
```python
import mlflow
import os

# Set tracking URI
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'
mlflow.set_tracking_uri('s3://loanpred-mlops-20251118-120330/mlruns')

# List all experiments
experiments = mlflow.search_experiments()
for exp in experiments:
    print(f"Experiment: {exp.name} (ID: {exp.experiment_id})")

# Get runs from specific experiment
runs = mlflow.search_runs(experiment_ids=['1'], order_by=['metrics.f1_score DESC'])
print("\nTop runs by F1 score:")
print(runs[['run_id', 'metrics.f1_score', 'metrics.accuracy', 'params.max_depth']].head())

# Get specific run details
run_id = runs.iloc[0]['run_id']
run = mlflow.get_run(run_id)
print(f"\nBest run ID: {run_id}")
print(f"F1 Score: {run.data.metrics['f1_score']}")
print(f"Accuracy: {run.data.metrics['accuracy']}")
```

### Option 3: View MLflow in Production Pods

**Access MLflow data inside running pods:**
```bash
# Get pod name
POD=$(kubectl get pod -l app=loan-prediction -n loan-prediction-mlops -o jsonpath='{.items[0].metadata.name}')

# List MLflow runs
kubectl exec $POD -n loan-prediction-mlops -- ls -la /app/mlruns

# View experiment metadata
kubectl exec $POD -n loan-prediction-mlops -- cat /app/mlruns/1/meta.yaml

# Copy MLflow runs to local machine
kubectl cp loan-prediction-mlops/$POD:/app/mlruns ./mlruns-backup
```

---

## Prometheus - Metrics Collection

Prometheus scrapes metrics from pods via annotations configured in deployment.yml.

### Check Prometheus Configuration

**Verify pod annotations:**
```bash
kubectl get pods -n loan-prediction-mlops -o yaml | grep -A 3 "prometheus.io"
```

Expected output:
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8005"
  prometheus.io/path: "/metrics"
```

### Option 1: Access Prometheus in Cluster (if deployed)

**Port forward Prometheus service:**
```bash
# Find Prometheus pod
kubectl get pods -n monitoring -l app=prometheus

# Port forward
kubectl port-forward -n monitoring svc/prometheus-service 9090:9090
```

**Access Prometheus UI:**
Open browser: http://localhost:9090

**Useful queries:**
```promql
# Request rate
rate(http_requests_total[5m])

# Prediction latency P95
histogram_quantile(0.95, rate(model_prediction_latency_seconds_bucket[5m]))

# Error rate
rate(model_prediction_errors_total[5m]) / rate(model_predictions_total[5m])

# Memory usage
container_memory_usage_bytes{pod=~"loan-prediction.*"} / container_spec_memory_limit_bytes

# CPU usage
rate(container_cpu_usage_seconds_total{pod=~"loan-prediction.*"}[5m])
```

### Option 2: Query Metrics Directly from Pods

**Get raw Prometheus metrics:**
```bash
# Get pod name
POD=$(kubectl get pod -l app=loan-prediction -n loan-prediction-mlops -o jsonpath='{.items[0].metadata.name}')

# Fetch metrics
kubectl exec $POD -n loan-prediction-mlops -- curl -s http://localhost:8005/metrics
```

**Example output:**
```
# HELP loan_predictions_total Total number of loan predictions made
# TYPE loan_predictions_total counter
loan_predictions_total{model_stage="Production"} 1523.0

# HELP model_prediction_latency_seconds Prediction latency in seconds
# TYPE model_prediction_latency_seconds histogram
model_prediction_latency_seconds_bucket{le="0.005"} 856.0
model_prediction_latency_seconds_bucket{le="0.01"} 1203.0
...
```

### Option 3: Port Forward to Pod for Live Metrics

**Access metrics via port-forward:**
```bash
kubectl port-forward -n loan-prediction-mlops $POD 8005:8005
```

**View in browser:**
- Metrics: http://localhost:8005/metrics
- Health: http://localhost:8005/health

---

## Grafana - Visualization

Grafana provides dashboards for visualizing Prometheus metrics.

### Option 1: Access Grafana in Cluster (if deployed)

**Port forward Grafana service:**
```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

**Access Grafana UI:**
- URL: http://localhost:3000
- Default credentials: admin/admin (change on first login)

### Option 2: Import Grafana Dashboards

**Find dashboard definitions:**
```bash
ls grafana/dashboards/
```

**Import dashboard steps:**
1. Login to Grafana
2. Click "+" → "Import"
3. Upload JSON file from `grafana/dashboards/`
4. Select Prometheus data source
5. Click "Import"

**Available dashboards:**
- Model Performance Dashboard
- API Metrics Dashboard
- Resource Usage Dashboard
- Fairness Metrics Dashboard

### Key Metrics to Monitor

**Model Performance:**
- F1 Score trend
- Accuracy over time
- Precision/Recall balance
- Prediction latency P50/P95/P99

**API Health:**
- Request rate (RPS)
- Error rate (%)
- Response time distribution
- Active connections

**Resource Usage:**
- CPU utilization (%)
- Memory consumption (MB)
- Pod restart count
- Network I/O

**Fairness Metrics:**
- Demographic parity difference
- Equalized odds difference
- Disparate impact ratio

---

## Fairlearn - Fairness Metrics

Fairlearn metrics are logged during training and stored in MLflow.

### View Fairness Metrics in MLflow

**Access fairness artifacts:**
```bash
# List fairness artifacts in best run
mlflow artifacts list --run-id <run_id> --artifact-path fairness
```

**Download fairness report:**
```bash
mlflow artifacts download --run-id <run_id> --artifact-path fairness/metrics.json -d ./fairness_reports
```

### Programmatic Access

**Python script to view fairness metrics:**
```python
import mlflow
import json

# Get best run
runs = mlflow.search_runs(order_by=['metrics.f1_score DESC'], max_results=1)
run_id = runs.iloc[0]['run_id']

# Download fairness metrics
client = mlflow.tracking.MlflowClient()
artifact_path = client.download_artifacts(run_id, 'fairness/metrics.json')

with open(artifact_path, 'r') as f:
    fairness_metrics = json.load(f)

print("Fairness Metrics:")
print(f"Demographic Parity Difference: {fairness_metrics['demographic_parity_difference']:.4f}")
print(f"Equalized Odds Difference: {fairness_metrics['equalized_odds_difference']:.4f}")
print(f"Disparate Impact: {fairness_metrics['disparate_impact']:.4f}")
```

### Fairness Dashboard

**View fairness in Grafana:**
If fairness metrics are exported to Prometheus, create dashboard panels:

```promql
# Demographic parity by sensitive feature
fairlearn_demographic_parity{sensitive_feature="Gender"}

# Equalized odds difference
fairlearn_equalized_odds_difference

# Disparate impact ratio
fairlearn_disparate_impact
```

---

## ML Metrics - Model Performance

### View Model Metrics via API

**Get model information:**
```bash
# Port forward to pod
POD=$(kubectl get pod -l app=loan-prediction -n loan-prediction-mlops -o jsonpath='{.items[0].metadata.name}')
kubectl port-forward -n loan-prediction-mlops $POD 8005:8005
```

**Query model info endpoint:**
```bash
curl http://localhost:8005/model/info | jq
```

**Example response:**
```json
{
  "model_name": "XGBoost",
  "model_stage": "Production",
  "model_version": "1",
  "metrics": {
    "f1_score": 0.8745,
    "accuracy": 0.8892,
    "precision": 0.8654,
    "recall": 0.8842,
    "roc_auc": 0.9123
  },
  "fairness": {
    "demographic_parity_difference": 0.0234,
    "equalized_odds_difference": 0.0156
  },
  "training_date": "2025-01-20T10:30:45Z",
  "mlflow_run_id": "abc123def456"
}
```

### View Historical Metrics

**Query MLflow for metric trends:**
```python
import mlflow
import pandas as pd
import matplotlib.pyplot as plt

# Search all runs
runs = mlflow.search_runs(experiment_ids=['1'])

# Extract metrics
metrics_df = runs[['run_id', 'start_time', 'metrics.f1_score',
                    'metrics.accuracy', 'metrics.precision', 'metrics.recall']]
metrics_df['start_time'] = pd.to_datetime(metrics_df['start_time'])
metrics_df = metrics_df.sort_values('start_time')

# Plot metric trends
plt.figure(figsize=(12, 6))
plt.plot(metrics_df['start_time'], metrics_df['metrics.f1_score'], label='F1 Score')
plt.plot(metrics_df['start_time'], metrics_df['metrics.accuracy'], label='Accuracy')
plt.xlabel('Training Date')
plt.ylabel('Metric Value')
plt.title('Model Performance Over Time')
plt.legend()
plt.grid(True)
plt.savefig('metric_trends.png')
plt.show()
```

### Compare Model Versions

**Compare Production vs Staging:**
```python
import mlflow

# Get Production model
production_runs = mlflow.search_runs(
    filter_string="tags.mlflow.runName LIKE '%Production%'",
    order_by=['start_time DESC'],
    max_results=1
)

# Get Staging model
staging_runs = mlflow.search_runs(
    filter_string="tags.mlflow.runName LIKE '%Staging%'",
    order_by=['start_time DESC'],
    max_results=1
)

print("Production Model:")
print(f"  F1: {production_runs.iloc[0]['metrics.f1_score']:.4f}")
print(f"  Accuracy: {production_runs.iloc[0]['metrics.accuracy']:.4f}")

print("\nStaging Model:")
print(f"  F1: {staging_runs.iloc[0]['metrics.f1_score']:.4f}")
print(f"  Accuracy: {staging_runs.iloc[0]['metrics.accuracy']:.4f}")
```

---

## API Endpoints

Direct API access for real-time metrics and predictions.

### Health Check

```bash
curl http://localhost:8005/health
```

Response:
```json
{"status": "ok"}
```

### Metrics Endpoint

```bash
curl http://localhost:8005/metrics
```

Returns Prometheus-formatted metrics.

### Model Info

```bash
curl http://localhost:8005/model/info
```

Returns model metadata and metrics.

### Make Prediction

```bash
curl -X POST http://localhost:8005/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Gender": "Male",
    "Married": "Yes",
    "Dependents": "0",
    "Education": "Graduate",
    "Self_Employed": "No",
    "ApplicantIncome": 5000,
    "CoapplicantIncome": 0,
    "LoanAmount": 150,
    "Loan_Amount_Term": 360,
    "Credit_History": 1.0,
    "Property_Area": "Urban"
  }'
```

Response:
```json
{
  "prediction": "Y",
  "probability": 0.8745,
  "model_version": "1",
  "prediction_time_ms": 45
}
```

---

## Quick Reference Commands

### MLflow
```bash
# Start MLflow UI (local)
mlflow ui --backend-store-uri ./mlruns

# Start MLflow UI (S3)
mlflow ui --backend-store-uri s3://loanpred-mlops-20251118-120330/mlruns

# List experiments
mlflow experiments list

# View run details
mlflow runs describe --run-id <run_id>
```

### Kubernetes Metrics
```bash
# Get all pods
kubectl get pods -n loan-prediction-mlops

# View pod logs
kubectl logs -f <pod-name> -n loan-prediction-mlops

# Get metrics from pod
kubectl exec <pod-name> -n loan-prediction-mlops -- curl http://localhost:8005/metrics

# Port forward to pod
kubectl port-forward -n loan-prediction-mlops <pod-name> 8005:8005
```

### Prometheus
```bash
# Port forward Prometheus
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Query metrics
curl 'http://localhost:9090/api/v1/query?query=up'
```

### Grafana
```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Access: http://localhost:3000
```

---

## Troubleshooting

### MLflow UI not showing runs
**Issue**: Empty MLflow UI
**Solution**:
```bash
# Check S3 bucket
aws s3 ls s3://loanpred-mlops-20251118-120330/mlruns/ --recursive

# Verify AWS credentials
aws sts get-caller-identity

# Check MLflow tracking URI
echo $MLFLOW_TRACKING_URI
```

### Prometheus not scraping pods
**Issue**: No metrics in Prometheus
**Solution**:
```bash
# Verify pod annotations
kubectl get pods -n loan-prediction-mlops -o yaml | grep prometheus

# Check if /metrics endpoint works
kubectl exec <pod-name> -n loan-prediction-mlops -- curl http://localhost:8005/metrics

# Verify Prometheus targets
# Open Prometheus UI → Status → Targets
```

### Grafana shows "No data"
**Issue**: Empty Grafana dashboards
**Solution**:
1. Check Prometheus data source connection
2. Verify query syntax (PromQL)
3. Adjust time range
4. Check if Prometheus has data: http://localhost:9090/graph

### Cannot access services
**Issue**: Port forward fails
**Solution**:
```bash
# Check if pod is running
kubectl get pods -n loan-prediction-mlops

# Check if service exists
kubectl get svc -n loan-prediction-mlops

# Try different port
kubectl port-forward -n loan-prediction-mlops <pod-name> 8080:8005
```

---

## Best Practices

1. **Regular Monitoring**: Check Grafana dashboards daily for anomalies
2. **Alert Configuration**: Set up Prometheus alerts for critical metrics
3. **Metric Retention**: Configure appropriate retention periods for metrics
4. **MLflow Cleanup**: Archive old experiments periodically
5. **Fairness Audits**: Review fairness metrics weekly
6. **Performance Baselines**: Establish baseline metrics for comparison
7. **Documentation**: Keep metric definitions and thresholds documented

---

## Next Steps

1. Set up Prometheus and Grafana in EKS (if not already deployed)
2. Configure Prometheus alerts based on `prometheus/rules/model-alerts.yml`
3. Create custom Grafana dashboards for specific use cases
4. Implement automated fairness testing in CI/CD
5. Set up metric alerting to Slack/Email

For deployment guides, see:
- [Prometheus Setup](../prometheus/README.md)
- [Grafana Setup](../grafana/README.md)
- [MLflow Server Setup](./MLFLOW_SERVER.md)
