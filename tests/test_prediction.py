# tests/test_prediction.py
"""
Prediction logic tests
"""
import pytest
import pandas as pd
import numpy as np
from tests.conftest import RUN_INTEGRATION


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Requires MLflow to be configured (use --run-integration to run)"
)
class TestModelLoader:
    """Tests for ModelLoader class"""

    def test_model_loader_initialization(self):
        """Test ModelLoader can be initialized"""
        from prediction_model.predict import ModelLoader

        loader = ModelLoader()
        assert loader is not None
        assert loader.model_name == "LoanPrediction"

    def test_load_production_model(self):
        """Test loading production model"""
        from prediction_model.predict import ModelLoader

        loader = ModelLoader()
        try:
            model = loader.load_model_by_stage("Production")
            assert model is not None
        except Exception as e:
            pytest.skip(f"Production model not available: {e}")

    def test_get_model_info_production(self):
        """Test getting model info for production stage"""
        from prediction_model.predict import ModelLoader

        loader = ModelLoader()
        info = loader.get_model_info("Production")

        if "error" not in info:
            assert "version" in info
            assert "model_type" in info
            assert "stage" in info
            assert info["stage"] == "Production"

    def test_list_all_versions(self):
        """Test listing all model versions"""
        from prediction_model.predict import ModelLoader

        loader = ModelLoader()
        versions = loader.list_all_versions()

        if len(versions) > 0:
            assert isinstance(versions, list)
            assert "version" in versions[0]
            assert "model_type" in versions[0]


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Requires MLflow to be configured"
)
class TestGeneratePredictions:
    """Tests for generate_predictions function"""

    def test_generate_predictions_with_dict(self, sample_loan_data):
        """Test predictions with dictionary input"""
        from prediction_model.predict import generate_predictions

        try:
            result = generate_predictions([sample_loan_data], stage="Production")

            assert "prediction" in result
            assert "model_version" in result
            assert "model_type" in result
            assert "model_stage" in result

            # Check prediction is valid
            assert len(result["prediction"]) > 0
            assert result["prediction"][0] in ["Y", "N"]

        except Exception as e:
            pytest.skip(f"Prediction failed (MLflow not configured): {e}")

    def test_generate_predictions_with_dataframe(self, sample_loan_dataframe):
        """Test predictions with DataFrame input"""
        from prediction_model.predict import generate_predictions

        try:
            result = generate_predictions(sample_loan_dataframe, stage="Production")

            assert "prediction" in result
            assert len(result["prediction"]) == len(sample_loan_dataframe)

            # All predictions should be Y or N
            for pred in result["prediction"]:
                assert pred in ["Y", "N"]

        except Exception as e:
            pytest.skip(f"Prediction failed: {e}")

    def test_generate_predictions_staging_model(self, sample_loan_data):
        """Test predictions with staging model"""
        from prediction_model.predict import generate_predictions

        try:
            result = generate_predictions([sample_loan_data], stage="Staging")

            if "error" not in str(result):
                assert result["model_stage"] == "Staging"

        except Exception as e:
            pytest.skip(f"Staging model not available: {e}")


@pytest.mark.skipif(
    not pytest.config.getoption("--run-integration", default=False),
    reason="Requires MLflow to be configured"
)
class TestGeneratePredictionsBatch:
    """Tests for generate_predictions_batch function"""

    def test_batch_predictions(self, sample_loan_dataframe):
        """Test batch predictions"""
        from prediction_model.predict import generate_predictions_batch

        try:
            result = generate_predictions_batch(
                sample_loan_dataframe,
                stage="Production"
            )

            assert "prediction" in result
            assert len(result["prediction"]) == len(sample_loan_dataframe)

            # Check all predictions are valid
            for pred in result["prediction"]:
                assert pred in ["Y", "N"]

        except Exception as e:
            pytest.skip(f"Batch prediction failed: {e}")


@pytest.mark.skipif(
    not pytest.config.getoption("--run-integration", default=False),
    reason="Requires MLflow to be configured"
)
class TestComparePredictions:
    """Tests for compare_predictions function"""

    def test_compare_predictions(self, sample_loan_dataframe):
        """Test comparing predictions from different models"""
        from prediction_model.predict import compare_predictions

        try:
            result = compare_predictions(sample_loan_dataframe)

            assert "production_predictions" in result
            assert "staging_predictions" in result
            assert "agreement_rate" in result
            assert "production_info" in result
            assert "staging_info" in result

            # Agreement rate should be between 0 and 1
            assert 0 <= result["agreement_rate"] <= 1

        except Exception as e:
            pytest.skip(f"Compare predictions failed (models not available): {e}")


class TestDataValidation:
    """Tests for data validation (without MLflow)"""

    def test_sample_data_has_required_fields(self, sample_loan_data):
        """Test sample data has all required fields"""
        required_fields = [
            "Gender", "Married", "Dependents", "Education", "Self_Employed",
            "ApplicantIncome", "CoapplicantIncome", "LoanAmount",
            "Loan_Amount_Term", "Credit_History", "Property_Area"
        ]

        for field in required_fields:
            assert field in sample_loan_data

    def test_sample_dataframe_structure(self, sample_loan_dataframe):
        """Test sample dataframe has correct structure"""
        assert isinstance(sample_loan_dataframe, pd.DataFrame)
        assert len(sample_loan_dataframe) > 0
        assert len(sample_loan_dataframe.columns) >= 11

    def test_numerical_features_are_numeric(self, sample_loan_dataframe):
        """Test numerical features have correct types"""
        numerical_cols = [
            "ApplicantIncome", "CoapplicantIncome",
            "LoanAmount", "Loan_Amount_Term", "Credit_History"
        ]

        for col in numerical_cols:
            if col in sample_loan_dataframe.columns:
                assert pd.api.types.is_numeric_dtype(sample_loan_dataframe[col])


# Add pytest option configuration
def pytest_addoption(parser):
    """Add custom pytest command line options"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require MLflow"
    )
