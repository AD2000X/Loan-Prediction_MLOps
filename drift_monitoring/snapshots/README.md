# Data Snapshots

This directory contains historical data snapshots for drift monitoring.

## Files

- `k8s_snapshot_YYYY-MM-DD.csv` - Data collected from K8s predictions on specific dates

## How to add new snapshots

Run the collection script and it will automatically save timestamped snapshots:

```bash
python collect_k8s_predictions.py
```

Commit the new snapshot files to Git:

```bash
git add drift_monitoring/snapshots/*.csv
git commit -m "Add new K8s prediction snapshot"
```
