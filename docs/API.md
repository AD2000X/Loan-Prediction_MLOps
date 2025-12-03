# API Documentation - Loan Prediction API

Complete API endpoint documentation and usage examples.

## Basic Information

- **Base URL**: `http://localhost:8005` (local) or `http://<ALB-DNS>` (AWS)
- **API Version**: v2.0.0
- **Framework**: FastAPI
- **Documentation**: `/docs` (Swagger UI) and `/redoc` (ReDoc)

---

## Endpoint Overview

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/` | GET | API Information | No |
| `/health` | GET | Health Check | No |
| `/metrics` | GET | Prometheus Metrics | No |
| `/prediction_api` | POST | Single Prediction | No |
| `/batch_prediction` | POST | Batch Prediction | No |
| `/model_info` | GET | Model Information | No |
| `/list_models` | GET | List All Models | No |

---

## Endpoint Details

### 1. Root Endpoint `/`

Get basic API information.

**Request**:
```bash
GET /
```

**Response**:
```json
{
  "message": "Loan Prediction API is running",
  "version": "2.0.0",
  "endpoints": {
    "health": "/health",
    "single_prediction": "/prediction_api",
    "batch_prediction": "/batch_prediction",
    "metrics": "/metrics"
  },
  "docs": "/docs"
}
```

---

### 2. Health Check `/health`

Used for Kubernetes liveness/readiness probes and monitoring systems.

**Request**:
```bash
GET /health
```

**Response**:
```json
{
  "status": "ok",
  "message": "Loan Prediction API is healthy",
  "timestamp": "2024-11-17T12:00:00.000000"
}
```

**Status Codes**:
- `200 OK`: Service healthy
- `500 Internal Server Error`: Service error

---

### 3. Prometheus Metrics `/metrics`

Expose metrics in Prometheus format for monitoring systems to scrape.

**Request**:
```bash
GET /metrics
```

**Response** (partial):
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",path="/prediction_api",status="200"} 42.0

# HELP model_predictions_total Total number of predictions made
# TYPE model_predictions_total counter
model_predictions_total{model_type="XGBoost",model_version="1",prediction="Y",stage="Production"} 25.0

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1",path="/prediction_api"} 30.0
```

**Available Metrics**:
- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request latency (histogram)
- `model_predictions_total`: Prediction count (by model version, type, result)
- `prediction_batch_size`: Batch prediction sample count
- `s3_upload_total`: S3 upload operation count

---

### 4. Single Prediction `/prediction_api`

Make prediction for a single loan application.

**Request**:
```bash
POST /prediction_api
Content-Type: application/json
```

**Request Body**:
```json
{
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
}
```

**Field Descriptions**:

| Field | Type | Valid Values | Description |
|-------|------|--------------|-------------|
| Gender | string | Male, Female | Gender |
| Married | string | Yes, No | Marital Status |
| Dependents | string | 0, 1, 2, 3+ | Number of Dependents |
| Education | string | Graduate, Not Graduate | Education Level |
| Self_Employed | string | Yes, No | Self-Employment Status |
| ApplicantIncome | integer | > 0 | Applicant Income |
| CoapplicantIncome | integer | >= 0 | Co-applicant Income |
| LoanAmount | integer | > 0 | Loan Amount (thousands) |
| Loan_Amount_Term | integer | 12, 36, 60, ... | Loan Term (months) |
| Credit_History | integer | 0, 1 | Credit History (1=good) |
| Property_Area | string | Urban, Semiurban, Rural | Property Area |

**Query Parameters**:
- `stage` (optional): `Production` or `Staging`, default `Production`

**Examples**:
```bash
# Use Production model
curl -X POST http://localhost:8005/prediction_api \
  -H "Content-Type: application/json" \
  -d @sample_request.json

# Use Staging model
curl -X POST "http://localhost:8005/prediction_api?stage=Staging" \
  -H "Content-Type: application/json" \
  -d @sample_request.json
```

**Response**:
```json
{
  "prediction": "Y",
  "model_version": "1",
  "model_type": "XGBoost",
  "model_stage": "Production",
  "timestamp": "2024-11-17T12:00:00.000000"
}
```

**Status Codes**:
- `200 OK`: Prediction successful
- `400 Bad Request`: Missing required fields or data format error
- `500 Internal Server Error`: Prediction failed (model error)

---

### 5. Batch Prediction `/batch_prediction`

Make predictions for batch loan applications, supports CSV file upload.

**Request**:
```bash
POST /batch_prediction
Content-Type: multipart/form-data
```

**Form Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| file | file | Yes | - | CSV file |
| stage | string | No | Production | Model stage |
| upload_to_s3 | boolean | No | false | Whether to upload to S3 |
| s3_bucket | string | Conditional | - | S3 bucket name (required when upload_to_s3=true) |

**CSV Format Requirements**:

CSV file should contain the same columns as single prediction (samples without headers will fail):

```csv
Gender,Married,Dependents,Education,Self_Employed,ApplicantIncome,CoapplicantIncome,LoanAmount,Loan_Amount_Term,Credit_History,Property_Area
Male,Yes,0,Graduate,No,5000,2000,150,360,1,Urban
Female,No,1,Not Graduate,Yes,4000,1500,120,360,1,Rural
```

**Examples**:

```bash
# Basic batch prediction
curl -X POST http://localhost:8005/batch_prediction \
  -F "file=@batch_data.csv"

# Using Staging model
curl -X POST http://localhost:8005/batch_prediction \
  -F "file=@batch_data.csv" \
  -F "stage=Staging"

# Upload results to S3
curl -X POST http://localhost:8005/batch_prediction \
  -F "file=@batch_data.csv" \
  -F "upload_to_s3=true" \
  -F "s3_bucket=my-bucket-name"
```

**Response**:

Returns CSV file containing original data + prediction results:

```csv
Gender,Married,...,Loan_Status_Prediction,Model_Version,Model_Type
Male,Yes,...,Y,1,XGBoost
Female,No,...,N,1,XGBoost
```

**Response Headers**:

| Header | Description |
|--------|-------------|
| Content-Type | `text/csv; charset=utf-8` |
| Content-Disposition | File download name |
| X-Model-Version | Model version used |
| X-Model-Type | Model type (XGBoost/LightGBM) |
| X-Model-Stage | Model stage |
| X-Batch-Size | Number of samples processed |
| X-S3-Key | S3 object key (if uploaded) |
| X-S3-Bucket | S3 bucket (if uploaded) |

**Python Example**:

```python
import requests

# Upload file
with open('batch_data.csv', 'rb') as f:
    files = {'file': f}
    data = {
        'stage': 'Production',
        'upload_to_s3': 'true',
        's3_bucket': 'my-bucket'
    }
    response = requests.post(
        'http://localhost:8005/batch_prediction',
        files=files,
        data=data
    )

# Save results
with open('predictions.csv', 'wb') as f:
    f.write(response.content)

# Check headers
print(f"Model: {response.headers['X-Model-Type']} v{response.headers['X-Model-Version']}")
print(f"Batch Size: {response.headers['X-Batch-Size']}")
if 'X-S3-Key' in response.headers:
    print(f"S3 Location: s3://{response.headers['X-S3-Bucket']}/{response.headers['X-S3-Key']}")
```

**Status Codes**:
- `200 OK`: Batch prediction successful
- `400 Bad Request`: File format error or missing parameters
- `422 Unprocessable Entity`: No file provided
- `500 Internal Server Error`: Prediction failed

---

### 6. Model Information `/model_info`

Get metadata for specified stage model.

**Request**:
```bash
GET /model_info?stage=Production
```

**Query Parameters**:
- `stage` (optional): `Production` or `Staging`, default `Production`

**Examples**:
```bash
curl "http://localhost:8005/model_info?stage=Production"
curl "http://localhost:8005/model_info?stage=Staging"
```

**Response**:
```json
{
  "version": "1",
  "stage": "Production",
  "model_type": "XGBoost",
  "f1_score": 0.8234,
  "accuracy": 0.8100,
  "recall": 0.8500,
  "precision": 0.7980,
  "run_id": "abc123def456",
  "description": "XGBoost model trained with hyperparameter optimization"
}
```

**Status Codes**:
- `200 OK`: Success
- `404 Not Found`: No model in specified stage
- `500 Internal Server Error`: MLflow connection failed

---

### 7. List All Models `/list_models`

List all available model versions in MLflow Registry.

**Request**:
```bash
GET /list_models
```

**Example**:
```bash
curl http://localhost:8005/list_models
```

**Response**:
```json
{
  "total_versions": 3,
  "models": [
    {
      "version": "3",
      "stage": "Staging",
      "model_type": "LightGBM",
      "f1_score": 0.8345,
      "run_id": "xyz789"
    },
    {
      "version": "2",
      "stage": "None",
      "model_type": "LightGBM",
      "f1_score": 0.8201,
      "run_id": "def456"
    },
    {
      "version": "1",
      "stage": "Production",
      "model_type": "XGBoost",
      "f1_score": 0.8234,
      "run_id": "abc123"
    }
  ]
}
```

---

## Error Handling

Errors return JSON in the form:
```json
{
  "detail": "Error message describing what went wrong"
}
```

Common cases:
- `400 Bad Request`: Missing required fields or invalid input
- `404 Not Found`: Model or resource not found
- `422 Unprocessable Entity`: Missing file for batch requests
- `500 Internal Server Error`: MLflow or server error

---

## API Changelog

### v2.0.0 (2024-11-17)
- Added batch prediction endpoint
- Added CORS support
- Added custom Prometheus metrics
- Added S3 upload functionality
- Added model information query endpoint
- Improved error handling

### v1.0.0 (2024-10-01)
- Initial release
- Single prediction functionality
- Health check endpoint
- Prometheus metrics integration
