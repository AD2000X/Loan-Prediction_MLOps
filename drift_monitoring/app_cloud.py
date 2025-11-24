# drift_monitoring/app_cloud.py
# Streamlit Cloud 版本：使用 Git 中的历史数据快照

import streamlit as st
import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently import ColumnMapping
import os
from pathlib import Path
import glob

# Streamlit App Settings
st.set_page_config(page_title="Loan Prediction Drift Monitor", layout="wide")
st.title("Loan Prediction Drift & Data Quality Monitor")

# Data directory
BASE_DIR = Path(__file__).parent
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
BASELINE_PATH = BASE_DIR / "baseline.csv"

# Load baseline
try:
    baseline = pd.read_csv(BASELINE_PATH)
    st.sidebar.success(f"Baseline loaded: {baseline.shape[0]} rows")
except Exception as e:
    st.error(f"Unable to load baseline: {e}")
    st.stop()

# Find all snapshot files
snapshot_files = sorted(glob.glob(str(SNAPSHOTS_DIR / "*.csv")), reverse=True)

if not snapshot_files:
    st.error("No snapshot files found in drift_monitoring/snapshots/")
    st.info("Run `python collect_k8s_predictions.py` to create snapshots, then commit to Git")
    st.stop()

# Snapshot selector
snapshot_options = {Path(f).name: f for f in snapshot_files}
selected_snapshot = st.sidebar.selectbox(
    "Select data snapshot",
    options=list(snapshot_options.keys()),
    help="Choose a snapshot to analyze for drift"
)

# Load selected snapshot
try:
    current = pd.read_csv(snapshot_options[selected_snapshot])
    st.sidebar.success(f"Current data loaded: {current.shape[0]} rows")
    st.write(f"**Analyzing**: {selected_snapshot}")
    st.write(f"Baseline shape: {baseline.shape}")
    st.write(f"Current batch shape: {current.shape}")
except Exception as e:
    st.error(f"Unable to load snapshot: {e}")
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
