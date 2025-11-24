# Prometheus Infrastructure Documentation

Prometheus collects and stores metrics from the loan prediction service.

## Configuration
- Deployment: Kubernetes (monitoring namespace)
- Scrape Interval: 15s
- Retention: 15 days

## Metrics Collected

### Model Performance Metrics
- model_f1_score{model_version, model_type, model_stage}
- model_accuracy{model_version, model_type, model_stage}
- model_recall{model_version, model_type, model_stage}
- model_precision{model_version, model_type, model_stage}

### Prediction Metrics
- model_predictions_total{model_version, model_type, model_stage, result}
- model_prediction_latency_seconds_bucket{model_version, model_type}
- model_prediction_errors_total{error_type, model_version}

### System Metrics
- HTTP request metrics (via prometheus_fastapi_instrumentator)
- Container metrics (CPU, memory)
- Pod health status

## Alert Rules
Location: prometheus/rules/model-alerts.yml

Critical Alerts:
- Model F1 score < 0.85
- Error rate > 5%
- Health check failed

Warning Alerts:
- High prediction latency > 0.5s
- No traffic for 5 minutes
- High memory/CPU usage > 85%

## Endpoints
- Metrics: /metrics on each pod (port 8005)
- Prometheus UI: kubectl port-forward -n monitoring svc/prometheus 9090:9090

## PromQL Query Examples
```
# Predictions per second
rate(model_predictions_total[1m])

# P95 latency
histogram_quantile(0.95, rate(model_prediction_latency_seconds_bucket[5m]))

# Error rate
rate(model_prediction_errors_total[5m]) / rate(model_predictions_total[5m])
```
