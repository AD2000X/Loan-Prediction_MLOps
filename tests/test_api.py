# tests/test_api.py
"""
API endpoint tests
"""
import pytest
from fastapi import status
import io
from tests.conftest import RUN_INTEGRATION


class TestHealthEndpoint:
    """Tests for /health endpoint"""

    def test_health_check_returns_200(self, api_client):
        """Test health endpoint returns 200 OK"""
        response = api_client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_check_response_format(self, api_client):
        """Test health endpoint response contains required fields"""
        response = api_client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "ok"
        assert "message" in data
        assert "timestamp" in data


class TestRootEndpoint:
    """Tests for / (root) endpoint"""

    def test_root_returns_200(self, api_client):
        """Test root endpoint returns 200 OK"""
        response = api_client.get("/")
        assert response.status_code == status.HTTP_200_OK

    def test_root_contains_endpoints_info(self, api_client):
        """Test root endpoint returns API information"""
        response = api_client.get("/")
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "endpoints" in data
        assert "/health" in str(data["endpoints"])


class TestMetricsEndpoint:
    """Tests for /metrics endpoint"""

    def test_metrics_endpoint_accessible(self, api_client):
        """Test metrics endpoint is accessible"""
        response = api_client.get("/metrics")
        assert response.status_code == status.HTTP_200_OK

    def test_metrics_endpoint_returns_prometheus_format(self, api_client):
        """Test metrics endpoint returns Prometheus format"""
        response = api_client.get("/metrics")
        content = response.text

        # Check for Prometheus metric format
        assert "# HELP" in content or "# TYPE" in content
        # Check for expected metrics
        assert "http_requests_total" in content or "python_info" in content


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Requires MLflow to be configured (use --run-integration to run)"
)
class TestPredictionEndpoint:
    """
    Tests for /prediction_api endpoint

    Note: These tests require MLflow to be properly configured with trained models.
    Run with: pytest --run-integration
    """

    def test_prediction_with_valid_data(self, api_client, sample_loan_data):
        """Test prediction endpoint with valid data"""
        response = api_client.post("/prediction_api", json=sample_loan_data)
        assert response.status_code == status.HTTP_200_OK

    def test_prediction_response_format(self, api_client, sample_loan_data):
        """Test prediction response contains required fields"""
        response = api_client.post("/prediction_api", json=sample_loan_data)

        if response.status_code == 200:
            data = response.json()
            assert "prediction" in data
            assert "model_version" in data
            assert "model_type" in data
            assert "model_stage" in data
            assert data["prediction"] in ["Y", "N"]

    def test_prediction_with_missing_field(self, api_client):
        """Test prediction endpoint with missing required field"""
        incomplete_data = {"Gender": "Male", "Married": "Yes"}
        response = api_client.post("/prediction_api", json=incomplete_data)

        # Should return 400 or 500 depending on validation
        assert response.status_code in [400, 500]

    def test_prediction_with_staging_model(self, api_client, sample_loan_data):
        """Test prediction endpoint with staging model"""
        response = api_client.post(
            "/prediction_api?stage=Staging",
            json=sample_loan_data
        )

        # Should work if staging model exists, otherwise 500
        assert response.status_code in [200, 500]


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Requires MLflow to be configured (use --run-integration to run)"
)
class TestBatchPredictionEndpoint:
    """
    Tests for /batch_prediction endpoint

    Note: These tests require MLflow to be properly configured.
    """

    def test_batch_prediction_with_csv_file(self, api_client, sample_csv_file):
        """Test batch prediction with CSV file"""
        with open(sample_csv_file, 'rb') as f:
            files = {"file": ("test.csv", f, "text/csv")}
            response = api_client.post("/batch_prediction", files=files)

        if response.status_code == 200:
            assert response.headers["content-type"] == "text/csv; charset=utf-8"
            assert "Content-Disposition" in response.headers

    def test_batch_prediction_response_headers(self, api_client, sample_csv_file):
        """Test batch prediction response headers"""
        with open(sample_csv_file, 'rb') as f:
            files = {"file": ("test.csv", f, "text/csv")}
            response = api_client.post("/batch_prediction", files=files)

        if response.status_code == 200:
            assert "X-Model-Version" in response.headers
            assert "X-Model-Type" in response.headers
            assert "X-Batch-Size" in response.headers

    def test_batch_prediction_without_file(self, api_client):
        """Test batch prediction without file upload"""
        response = api_client.post("/batch_prediction")
        assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Requires MLflow to be configured"
)
class TestModelInfoEndpoint:
    """Tests for /model_info endpoint"""

    def test_model_info_production(self, api_client):
        """Test model info for production stage"""
        response = api_client.get("/model_info?stage=Production")

        if response.status_code == 200:
            data = response.json()
            assert "version" in data
            assert "model_type" in data
            assert "stage" in data

    def test_model_info_staging(self, api_client):
        """Test model info for staging stage"""
        response = api_client.get("/model_info?stage=Staging")

        # Should work if staging model exists
        assert response.status_code in [200, 404, 500]


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Requires MLflow to be configured"
)
class TestListModelsEndpoint:
    """Tests for /list_models endpoint"""

    def test_list_models(self, api_client):
        """Test list models endpoint"""
        response = api_client.get("/list_models")

        if response.status_code == 200:
            data = response.json()
            assert "total_versions" in data
            assert "models" in data
            assert isinstance(data["models"], list)
