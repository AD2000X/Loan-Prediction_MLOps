# Grafana Infrastructure Documentation

Grafana provides visualization and dashboarding for ML model monitoring.

## Configuration
- Deployment: docker-compose in `monitoring/` (Grafana on port 3000:3000)
- Data Source: Prometheus (from `monitoring/prometheus/prometheus.yml`)

## Dashboards

### Model Performance Dashboard
Location: grafana/dashboards/model-performance.json

Panels:
- Model F1 Score (gauge)
- Model Accuracy (gauge)
- Predictions per Minute (graph)
- Prediction Distribution (pie chart)
- Model Metrics Comparison (table)

### Key Metrics Monitored
- model_predictions_total
- prediction_batch_size
- s3_upload_total
- http_* metrics from prometheus_fastapi_instrumentator

## Access
- Local compose: http://localhost:3000 (admin/admin by default)

## Alert Integration
Grafana can connect to Prometheus Alertmanager if configured (not provisioned in this repo).
