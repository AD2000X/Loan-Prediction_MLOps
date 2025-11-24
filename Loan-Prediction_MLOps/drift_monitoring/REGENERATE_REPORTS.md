# How to Regenerate Drift Reports

Drift report HTML files are no longer tracked in Git to avoid inflating repository language statistics. These reports can be easily regenerated locally when needed.

## Generate Reports Locally

### Option 1: Using Streamlit App with S3 Data
```bash
cd drift_monitoring
streamlit run app_v1.py
```
1. Open browser at http://localhost:8501
2. Select baseline and current data from S3
3. Click "Generate Report" button
4. HTML report will be created as `drift_report_temp.html`

### Option 2: Using Streamlit App with Local Snapshots
```bash
cd drift_monitoring
streamlit run app_cloud.py
```
1. Open browser at http://localhost:8501
2. Select from available snapshots in dropdown
3. Report will be automatically generated
4. HTML files created in `drift_monitoring/` directory

### Option 3: Programmatically
```python
from evidently import Report
from evidently.metrics import DataDriftPreset, DataQualityPreset
import pandas as pd

# Load your data
baseline = pd.read_csv("baseline.csv")
current = pd.read_csv("current.csv")

# Generate report
report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
report.run(reference_data=baseline, current_data=current)

# Save as HTML
report.save_html("drift_report.html")
```

## Generated Files

The following HTML files may be created:
- `drift_monitoring/drift_report.html`
- `drift_monitoring/drift_report_temp.html`
- `report/drift_report_temp.html`

These are automatically ignored by Git via `.gitignore`.

## Note

The HTML reports are large (~440KB+) and consist mostly of embedded JavaScript/CSS for interactive visualizations. Keeping them out of version control helps maintain accurate language statistics on GitHub.