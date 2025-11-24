# Grafana Infrastructure Documentation

Grafana provides visualization and dashboarding for ML model monitoring.

## Configuration
- Deployment: Kubernetes (monitoring namespace)
- Data Source: Prometheus
- Port: 3000

## Dashboards

### Model Performance Dashboard
Location: grafana/dashboards/model-performance.json

Panels:
- Model F1 Score (gauge)
- Model Accuracy (gauge)
- Predictions per Minute (graph)
- Prediction Latency P95 (graph)
- Error Rate (graph)
- Prediction Distribution (pie chart)
- Model Metrics Comparison (table)

### Key Metrics Monitored
- model_f1_score
- model_accuracy
- model_prediction_latency_seconds
- model_predictions_total
- model_prediction_errors_total

## Access
Port-forward: kubectl port-forward -n monitoring svc/grafana 3000:80

## Alert Integration
Grafana connects to Prometheus Alertmanager for alert notifications.
