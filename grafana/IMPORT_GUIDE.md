# Grafana Dashboard Import Guide

Complete guide for importing and configuring Grafana dashboards for the Loan Prediction MLOps project.

---

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Import Steps](#quick-import-steps)
- [Dashboard 1: FastAPI Monitoring](#dashboard-1-fastapi-monitoring)
- [Dashboard 2: Kubernetes Cluster Monitoring](#dashboard-2-kubernetes-cluster-monitoring)
- [Verification](#verification)
- [PromQL Queries Explained](#promql-queries-explained)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before importing the dashboards, ensure:

1. **Grafana is running and accessible**
   ```bash
   kubectl port-forward -n monitoring svc/kube-prom-grafana 3001:80
   ```
   Access: http://localhost:3001

2. **Prometheus data source is configured**
   - Navigate to: **Connections → Data sources**
   - Verify "Prometheus" data source exists and is working
   - Test the connection (should show green checkmark)

3. **ServiceMonitor is deployed**
   ```bash
   kubectl get servicemonitor -n monitoring
   ```
   Should show: `loan-prediction`

4. **Metrics are being collected**
   ```bash
   # Check if metrics endpoint is accessible
   curl http://localhost:8006/metrics
   ```

---

## Quick Import Steps

### Step 1: Access Grafana Dashboard Import

1. Open Grafana: http://localhost:3001
2. Login (default: admin / prom-operator)
3. Click **"Dashboards"** in the left sidebar
4. Click **"New" → "Import"**

### Step 2: Import FastAPI Dashboard

1. Click **"Upload dashboard JSON file"**
2. Select `grafana/fastapi-dashboard.json`
3. On the import screen:
   - **Name**: Loan Prediction - FastAPI Monitoring
   - **Folder**: (Optional) Create folder "Loan Prediction"
   - **Data Source**: Select "Prometheus"
4. Click **"Import"**

### Step 3: Import Kubernetes Dashboard

1. Repeat Step 1 to access import page
2. Select `grafana/k8s-cluster-dashboard.json`
3. On the import screen:
   - **Name**: Kubernetes Cluster Monitoring (via Prometheus)
   - **Folder**: Same folder as above
   - **Data Source**: Select "Prometheus"
4. Click **"Import"**

### Step 4: Verify Data

- Both dashboards should immediately show data
- If panels show "No Data", see [Troubleshooting](#troubleshooting)

---

## Dashboard 1: FastAPI Monitoring

### Overview
Monitors the FastAPI application performance and prediction API metrics.

### Panels Included

#### 1. Total requests in server (Pie Chart)
**Purpose**: Shows distribution of requests across different API endpoints

**Metrics**:
- `/prediction_api` - Single predictions
- `/batch_prediction` - Batch predictions
- `/health` - Health checks
- `/metrics` - Prometheus scraping

**What to watch**:
- High proportion of `/health` requests is normal
- `/prediction_api` should dominate business requests

#### 2. Requests created (Time Series)
**Purpose**: Real-time request rate per endpoint

**Metrics**: Requests per second (req/s) for each endpoint

**What to watch**:
- Sudden spikes may indicate traffic surge
- Drops to zero indicate service issues

#### 3. Batch prediction calls (Gauge)
**Purpose**: Total number of predictions made in the selected time range

**Metrics**: Sum of all model predictions

**What to watch**:
- Steadily increasing = healthy usage
- Stuck at zero = no prediction traffic

#### 4. Latency (Time Series)
**Purpose**: API response time percentiles

**Metrics**:
- **p50 (median)**: 50% of requests complete under this time
- **p95**: 95% of requests complete under this time
- **p99**: 99% of requests complete under this time

**What to watch**:
- p50 should stay under 100ms
- p95 should stay under 500ms
- p99 spikes indicate occasional slow requests

---

## Dashboard 2: Kubernetes Cluster Monitoring

### Overview
Monitors Kubernetes cluster resources for the loan-prediction-mlops namespace.

### Panels Included

#### 1. Network I/O pressure (Time Series)
**Purpose**: Cluster network traffic

**Metrics**:
- Network receive (green): Incoming traffic
- Network transmit (yellow): Outgoing traffic

**What to watch**:
- Sudden spikes may indicate data transfer issues
- Sustained high traffic may need bandwidth upgrade

#### 2. Cluster memory usage (Gauge)
**Purpose**: Percentage of cluster memory used by the application

**Thresholds**:
- Green (0-60%): Healthy
- Yellow (60-80%): Warning
- Red (80-100%): Critical

**What to watch**:
- Consistently above 80% = need more memory
- Sudden increases may indicate memory leak

#### 3. Cluster CPU usage (Gauge)
**Purpose**: Total CPU cores used by the application (2-minute average)

**What to watch**:
- Normal range: 0.1 - 2.0 cores
- Above 4 cores = high load or inefficient code

#### 4. Cluster filesystem usage (Stat)
**Purpose**: Total filesystem space used

**What to watch**:
- Steadily increasing = logs/data accumulation
- Rapid growth = investigate disk usage

#### 5. Pods CPU usage (Time Series)
**Purpose**: CPU usage per pod

**What to watch**:
- All pods should have similar CPU usage
- One pod with high CPU = potential issue

#### 6. Containers CPU usage (Time Series)
**Purpose**: Detailed CPU usage per container within pods

**What to watch**:
- Useful for identifying which container is consuming resources
- Format: `pod-name/container-name`

---

## Verification

### Check 1: Metrics Availability

Run in Grafana's **Explore** view:

```promql
# Should return your FastAPI metrics
up{namespace="loan-prediction-mlops"}

# Should return HTTP request metrics
http_requests_total{namespace="loan-prediction-mlops"}

# Should return custom prediction metrics
model_predictions_total{namespace="loan-prediction-mlops"}
```

### Check 2: Generate Test Traffic

```bash
# Send test prediction request
curl -X POST http://localhost:8006/prediction_api \
  -H "Content-Type: application/json" \
  -d '{
    "Gender": "Male",
    "Married": "Yes",
    "Dependents": "0",
    "Education": "Graduate",
    "Self_Employed": "No",
    "ApplicantIncome": 5000,
    "CoapplicantIncome": 2000,
    "LoanAmount": 150,
    "Loan_Amount_Term": 360,
    "Credit_History": 1,
    "Property_Area": "Urban"
  }'
```

Wait 15 seconds (Prometheus scrape interval), then check dashboard for updated metrics.

### Check 3: Time Range

- Default time range: **Last 6 hours**
- Auto-refresh: **Every 10 seconds**
- Adjust in top-right corner if needed

---

## PromQL Queries Explained

### FastAPI Dashboard Queries

#### Total requests in server (Pie chart)
```promql
sum by (handler) (increase(http_requests_total{namespace="loan-prediction-mlops"}[$__range]))
```
- `increase()`: Total count over time range
- `sum by (handler)`: Group by endpoint path
- `$__range`: Grafana variable for selected time range

#### Requests created (Time series)
```promql
rate(http_requests_total{namespace="loan-prediction-mlops"}[5m])
```
- `rate()`: Per-second average over 5 minutes
- Returns requests/second for each endpoint

#### Batch prediction calls (Gauge)
```promql
sum(increase(model_predictions_total{namespace="loan-prediction-mlops"}[$__range]))
```
- Custom metric from `main.py`
- Counts all predictions (Y + N)

#### Latency - p50 (Time series)
```promql
histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{namespace="loan-prediction-mlops"}[5m])) by (le, handler))
```
- `histogram_quantile()`: Calculates percentile from histogram buckets
- `0.50`: 50th percentile (median)
- `le`: Less-than-or-equal bucket labels
- `by (le, handler)`: Preserve buckets and endpoint

#### Latency - p95 & p99
Same as p50, but with `0.95` and `0.99`

### Kubernetes Dashboard Queries

#### Network I/O pressure
```promql
# Receive
sum(rate(container_network_receive_bytes_total{namespace="loan-prediction-mlops"}[5m]))

# Transmit
sum(rate(container_network_transmit_bytes_total{namespace="loan-prediction-mlops"}[5m]))
```
- Returns bytes/second
- Aggregated across all containers

#### Cluster memory usage
```promql
sum(container_memory_working_set_bytes{namespace="loan-prediction-mlops", container!=""}) / sum(kube_node_status_capacity{resource="memory"}) * 100
```
- `container_memory_working_set_bytes`: Actual memory in use
- `kube_node_status_capacity`: Total available memory
- Result: Percentage (0-100%)

#### Cluster CPU usage
```promql
sum(rate(container_cpu_usage_seconds_total{namespace="loan-prediction-mlops", container!=""}[2m]))
```
- `rate()` over 2 minutes: Average CPU cores used
- Result: Number of CPU cores (e.g., 0.5 = half a core)

#### Pods/Containers CPU usage
```promql
sum(rate(container_cpu_usage_seconds_total{namespace="loan-prediction-mlops", pod!="", container!=""}[2m])) by (pod)
```
- `by (pod)`: Separate line for each pod
- Container query adds `by (pod, container)`

---

## Troubleshooting

### Problem: "No Data" in panels

**Solution 1: Check ServiceMonitor**
```bash
kubectl get servicemonitor loan-prediction -n monitoring -o yaml
```
Verify:
- `namespaceSelector.matchNames: ["loan-prediction-mlops"]`
- `selector.matchLabels.app: loan-prediction`
- `endpoints.path: /metrics`

**Solution 2: Check Service Labels**
```bash
kubectl get svc loan-prediction-service -n loan-prediction-mlops --show-labels
```
Must have label: `app=loan-prediction`

If missing, add it:
```bash
kubectl label svc loan-prediction-service -n loan-prediction-mlops app=loan-prediction
```

**Solution 3: Verify Prometheus Target**
```bash
kubectl port-forward -n monitoring svc/kube-prom-prometheus 9090:9090
```
Visit: http://localhost:9090/targets

Search for "loan-prediction", status should be "UP"

### Problem: Metrics exist but values are zero

**Cause**: No traffic to the application

**Solution**: Generate test traffic (see [Verification](#verification))

### Problem: Only Kubernetes metrics work, FastAPI metrics missing

**Cause**: FastAPI metrics not being scraped

**Debug Steps**:
1. Check metrics endpoint directly:
   ```bash
   curl http://localhost:8006/metrics | grep model_predictions
   ```
   Should return lines like:
   ```
   model_predictions_total{...} 5
   ```

2. Check Prometheus scraping:
   ```bash
   # In Grafana Explore
   up{job="loan-prediction", namespace="loan-prediction-mlops"}
   ```
   Should return `1` (UP)

3. Restart ServiceMonitor:
   ```bash
   kubectl delete servicemonitor loan-prediction -n monitoring
   kubectl apply -f k8s/servicemonitor-loan-prediction.yaml
   ```

### Problem: Latency queries show "No Data"

**Cause**: `http_request_duration_seconds_bucket` metric not available

**Solution**:
Prometheus Instrumentator (in `main.py`) should create these automatically.

Verify in metrics endpoint:
```bash
curl http://localhost:8006/metrics | grep http_request_duration_seconds_bucket
```

If missing, the Instrumentator may not be properly initialized.

### Problem: Dashboard shows but data is delayed

**Cause**: Prometheus scrape interval is 15 seconds

**Not a problem**: This is normal behavior. Metrics update every 15 seconds.

To see faster updates, reduce `interval` in ServiceMonitor (not recommended for production).

---

## Advanced Configuration

### Change Refresh Rate

1. Click the refresh icon (top-right)
2. Select interval (5s, 10s, 30s, 1m, etc.)
3. Note: Faster refresh = more Prometheus queries

### Add Alerts

1. Click on any panel → **Edit**
2. Go to **Alert** tab
3. Create alert rule (e.g., "Latency > 1 second")
4. Configure notification channel (email, Slack, etc.)

### Customize Panels

1. Click on panel title → **Edit**
2. Modify:
   - Query (PromQL)
   - Visualization type
   - Thresholds
   - Legend format
3. **Save** dashboard

### Export Modified Dashboard

1. Dashboard settings (gear icon, top-right)
2. **JSON Model**
3. Copy JSON
4. Save to file for version control

---

## Next Steps

1. **Set up alerts** for critical metrics (latency, error rate)
2. **Create additional panels** for business metrics (predictions by outcome, model version)
3. **Add variables** to filter by model version or time range
4. **Share dashboards** with your team via Grafana links

---

## Support

If you encounter issues not covered here:
1. Check Grafana logs: `kubectl logs -n monitoring deployment/kube-prom-grafana`
2. Check Prometheus logs: `kubectl logs -n monitoring statefulset/prometheus-kube-prom-prometheus`
3. Verify metrics in Prometheus UI: http://localhost:9090/graph

---

**Dashboard Versions:**
- FastAPI Monitoring: v1.0
- Kubernetes Cluster Monitoring: v1.0
- Last Updated: 2025-11-21
