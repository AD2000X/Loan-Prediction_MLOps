# drift_monitoring/app_v1.py

import streamlit as st
import pandas as pd
import boto3
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently import ColumnMapping
import os


# Streamlit App Settings
st.set_page_config(page_title="Loan Prediction Drift Monitor", layout="wide")
st.title("Loan Prediction Drift & Data Quality Monitor")


# Data source settings
use_s3 = st.sidebar.checkbox("Load data from S3", value=False)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
baseline_path = os.path.join(BASE_DIR, "baseline.csv")
batch_path = os.path.join(BASE_DIR, "latest_batch.csv")

if use_s3:
    s3_bucket = st.sidebar.text_input("S3 Bucket name", value="your-bucket-name")
    baseline_key = st.sidebar.text_input("Baseline Key", value="monitoring/baseline.csv")
    batch_key = st.sidebar.text_input("Latest Batch Key", value="monitoring/latest_batch.csv")

    if st.sidebar.button("Download from S3"):
        s3 = boto3.client("s3")
        try:
            s3.download_file(s3_bucket, baseline_key, baseline_path)
            s3.download_file(s3_bucket, batch_key, batch_path)
            st.success("Downloaded the latest baseline and batch files from S3")
        except Exception as e:
            st.error(f"Failed to download from S3: {e}")
            st.stop()


# Load CSVs
try:
    baseline = pd.read_csv(baseline_path)
    current = pd.read_csv(batch_path)
    st.success("Successfully loaded baseline and batch data")
    st.write(f"Baseline shape: {baseline.shape}")
    st.write(f"Current batch shape: {current.shape}")
except Exception as e:
    st.error(f"Unable to load baseline/batch data: {e}")
    st.stop()


# Auto-detect columns for mapping
def detect_columns(df):
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    return numeric_cols, categorical_cols

target_candidates = [col for col in baseline.columns if "status" in col.lower() or "target" in col.lower()]
target_col = target_candidates[0] if target_candidates else None

num_features, cat_features = detect_columns(baseline)
if target_col and target_col in num_features:
    num_features.remove(target_col)
if target_col and target_col in cat_features:
    cat_features.remove(target_col)

column_mapping = ColumnMapping(
    target=target_col,
    prediction=None,
    numerical_features=num_features,
    categorical_features=cat_features
)


# Validate dataset columns
missing_in_current = [c for c in baseline.columns if c not in current.columns]
if missing_in_current:
    st.warning(f"The following columns are missing in current data: {missing_in_current}")
    baseline = baseline.drop(columns=missing_in_current, errors="ignore")

# Align columns
common_cols = [c for c in baseline.columns if c in current.columns]
baseline = baseline[common_cols]
current = current[common_cols]


# Generate Evidently Report
st.header("Data Drift Report")

try:
    report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
    report.run(reference_data=baseline, current_data=current, column_mapping=column_mapping)

    html_path = "drift_report_temp.html"
    report.save_html(html_path)

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    st.components.v1.html(html_content, height=1000, scrolling=True)

except Exception as e:
    st.error(f"Error generating report: {e}")
    st.stop()


# Export Report Option
if st.sidebar.button("Export report"):
    try:
        report.save_html("drift_report.html")
        st.sidebar.success("Report saved as drift_report.html")
    except Exception as e:
        st.sidebar.error(f"Failed to save report: {e}")