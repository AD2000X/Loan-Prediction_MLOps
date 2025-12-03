# Prometheus Infrastructure Documentation

Prometheus collects and stores metrics from the loan prediction service.

## Configuration
- Deployment: docker-compose in `monitoring/`
- Scrape target (default dev): `host.docker.internal:8005` on `/metrics`
- Scrape Interval: 10s (loan-prediction local job)
- Retention: default Prometheus settings (not overridden)

## Metrics Collected (from app)
- http_* metrics from prometheus_fastapi_instrumentator
- model_predictions_total{model_version, model_type, prediction, stage}
- prediction_batch_size (gauge)
- s3_upload_total{status}

## Alert Rules
Location: prometheus/rules/model-alerts.yml

Critical Alerts:
- Model F1 score < 0.85 (note: requires model_f1_score metric, not emitted by current app)
- Error rate > 5% (requires model_prediction_errors_total metric, not emitted)
- Health check failed

Warning Alerts:
- High prediction latency > 0.5s (requires latency histogram, not emitted)
- No traffic for 5 minutes
- High memory/CPU usage > 85%

## Endpoints
- Metrics: /metrics on each pod (port 8005)
- Prometheus UI: kubectl port-forward -n monitoring svc/prometheus 9090:9090

## PromQL Query Examples
```
# Predictions per second
rate(model_predictions_total[1m])

# Requests per second
rate(http_requests_total[1m])

# Batch size gauge
prediction_batch_size
```
