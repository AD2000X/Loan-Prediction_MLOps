# Monitoring System - Prometheus & Grafana

This monitoring system provides comprehensive performance monitoring and visualization for the Loan Prediction API.

## Architecture Overview

```
┌─────────────────┐
│  Loan Pred API  │──┐
│   (port 8005)   │  │
│  /metrics       │  │  scrape metrics
└─────────────────┘  │
                     ▼
              ┌──────────────┐
              │  Prometheus  │
              │  (port 9090) │
              └──────┬───────┘
                     │
                     │ query
                     ▼
              ┌──────────────┐
              │   Grafana    │
              │  (port 3000) │
              └──────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Loan Prediction API running (optional, for live metrics)

### Start All Services

```bash
cd monitoring
docker-compose up -d
```

### Access Services

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Stop Services

```bash
docker-compose down
```

## Components

### 1. Prometheus

Time-series database for metrics collection.

**Configuration**: `prometheus/prometheus.yml`

**Key Features**:
- Scrapes metrics from FastAPI `/metrics` endpoint
- 15-second scrape interval
- Data retention: 15 days

**Check Targets**:
```
http://localhost:9090/targets
```

### 2. Grafana

Visualization platform for metrics.

**Default Credentials**:
- Username: `admin`
- Password: `admin`

**Pre-configured Dashboards**:
- Loan Prediction API Metrics
- Request Performance
- Model Predictions

### 3. FastAPI Metrics

The API exposes metrics at `/metrics` endpoint.

**Available Metrics**:

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | Request latency |
| `prediction_requests_total` | Counter | Total predictions |
| `active_requests` | Gauge | Currently active requests |
| `model_predictions_total` | Counter | Predictions by result |

## Dashboard Setup

### Import Dashboard

1. Open Grafana: http://localhost:3000
2. Login with admin/admin
3. Navigate to Dashboards → Import
4. Upload JSON file from `../grafana/dashboards/`
5. Select Prometheus data source
6. Click Import

### Available Dashboards

1. **loan-prediction-api.json**: Main API metrics
2. **model-performance.json**: ML model metrics
3. **system-health.json**: System resources

## Custom Queries

### Prometheus Queries

**Request Rate**:
```promql
rate(http_requests_total[5m])
```

**95th Percentile Latency**:
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Prediction Distribution**:
```promql
sum by (prediction) (increase(model_predictions_total[1h]))
```

**Error Rate**:
```promql
rate(http_requests_total{status=~"5.."}[5m])
```

## Alerting

### Alert Rules

Configure in `prometheus/alert_rules.yml`:

```yaml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "High API latency"
```

### Grafana Alerts

1. Edit panel → Alert tab
2. Configure conditions
3. Add notification channels

## Kubernetes Integration

### Deploy to Kubernetes

```bash
kubectl apply -f k8s/monitoring/
```

### ServiceMonitor for Prometheus Operator

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: loan-prediction-api
spec:
  selector:
    matchLabels:
      app: loan-prediction
  endpoints:
    - port: metrics
      interval: 30s
```

## Performance Optimization

### Prometheus Storage

Adjust retention in `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'loan-prediction'

storage:
  tsdb:
    retention.time: 30d
    retention.size: 10GB
```

### Grafana Performance

1. Enable caching in `grafana.ini`
2. Use appropriate time ranges
3. Optimize dashboard queries

## Troubleshooting

### Common Issues

**Prometheus Not Scraping**:
- Check target status: http://localhost:9090/targets
- Verify API is running: http://localhost:8005/metrics
- Check network connectivity

**Grafana No Data**:
- Verify Prometheus data source
- Check time range selection
- Validate query syntax

**High Memory Usage**:
- Reduce retention period
- Increase scrape interval
- Optimize queries

### Logs

```bash
# Prometheus logs
docker-compose logs prometheus

# Grafana logs
docker-compose logs grafana

# All services
docker-compose logs -f
```

## Backup and Recovery

### Backup Prometheus Data

```bash
docker exec prometheus tar czf /tmp/prometheus-backup.tar.gz /prometheus
docker cp prometheus:/tmp/prometheus-backup.tar.gz ./backup/
```

### Backup Grafana Dashboards

```bash
# Export via UI: Settings → Dashboards → Export

# Or via API:
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3000/api/dashboards/uid/$DASHBOARD_UID \
  > dashboard-backup.json
```

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [FastAPI Metrics Guide](https://prometheus.github.io/client_python/)
- [Docker Compose Reference](https://docs.docker.com/compose/)