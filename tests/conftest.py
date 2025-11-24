# tests/conftest.py
"""
Pytest configuration and shared fixtures
"""
import pytest
import pandas as pd
from fastapi.testclient import TestClient

# Flag controlled by --run-integration CLI option
RUN_INTEGRATION = False


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require MLflow models",
    )


def pytest_configure(config):
    global RUN_INTEGRATION
    RUN_INTEGRATION = config.getoption("--run-integration")


@pytest.fixture
def sample_loan_data():
    """
    Sample loan application data for testing
    """
    return {
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


@pytest.fixture
def sample_loan_dataframe():
    """
    Sample loan application data as DataFrame
    """
    data = {
        "Gender": ["Male", "Female"],
        "Married": ["Yes", "No"],
        "Dependents": ["0", "1"],
        "Education": ["Graduate", "Not Graduate"],
        "Self_Employed": ["No", "Yes"],
        "ApplicantIncome": [5000, 4000],
        "CoapplicantIncome": [2000, 1500],
        "LoanAmount": [150, 120],
        "Loan_Amount_Term": [360, 360],
        "Credit_History": [1, 1],
        "Property_Area": ["Urban", "Rural"]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_csv_file(tmp_path, sample_loan_dataframe):
    """
    Create a temporary CSV file for testing batch predictions
    """
    csv_path = tmp_path / "test_data.csv"
    sample_loan_dataframe.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def api_client():
    """
    FastAPI test client
    Note: Import here to avoid import errors if MLflow is not configured
    """
    from main import app
    return TestClient(app)
