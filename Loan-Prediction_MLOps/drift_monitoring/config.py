# drift_monitoring/config.py
"""
Configuration for Drift Monitoring System
"""
import os

# S3 Configuration
S3_BUCKET = os.getenv("DRIFT_S3_BUCKET", "your-bucket-name")
S3_BASELINE_KEY = "monitoring/baseline.csv"
S3_BATCH_PREFIX = "predictions/"

# Drift Detection Thresholds
DRIFT_THRESHOLD = 0.5  # Threshold for detecting drift (0-1)
DATA_QUALITY_THRESHOLD = 0.8  # Minimum data quality score

# Feature Configuration
NUMERICAL_FEATURES = [
    "ApplicantIncome",
    "CoapplicantIncome",
    "LoanAmount",
    "Loan_Amount_Term",
    "Credit_History"
]

CATEGORICAL_FEATURES = [
    "Gender",
    "Married",
    "Dependents",
    "Education",
    "Self_Employed",
    "Property_Area"
]

TARGET_COLUMN = "Loan_Status"

# Report Configuration
REPORT_OUTPUT_PATH = "reports/"
REPORT_RETENTION_DAYS = 30

# Streamlit UI Configuration
APP_TITLE = "Loan Prediction - Data Drift Monitor"
APP_LAYOUT = "wide"
SIDEBAR_STATE = "expanded"

# Monitoring Schedule
MONITORING_FREQUENCY_HOURS = 24  # How often to check for drift
