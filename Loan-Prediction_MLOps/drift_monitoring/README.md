# Data Drift Monitoring with Evidently.ai

Monitor data drift and data quality issues in production environment.

## Features

- Data drift detection
- Data quality analysis
- Support for local files and S3 data sources
- HTML report export
- Interactive visualizations

## Quick Start

### Local Execution

```bash
cd drift_monitoring

# Install dependencies
pip install -r requirements.txt

# Run Streamlit application
streamlit run app_v1.py
```

Access: http://localhost:8501

### Docker Execution

```bash
cd drift_monitoring

# Build image
docker build -t drift-monitoring:latest .

# Run container
docker run -p 8501:8501 drift-monitoring:latest
```

## Configuration

Configuration is managed through `config.py`:

- S3 bucket settings for batch data
- Drift detection thresholds
- Feature definitions
- Report output settings

## Usage

### Data Sources

1. **Local Files**: Upload CSV files directly through the UI
2. **S3 Integration**: Automatically fetch batch data from S3
3. **Baseline Data**: Uses stored baseline for comparison

### Report Types

- **Data Drift Report**: Statistical comparison between baseline and current data
- **Data Quality Report**: Missing values, data types, and distribution analysis

### Workflow

1. Select data source (local file or S3)
2. Configure report parameters
3. Generate report
4. View interactive visualizations
5. Export HTML report (optional)

## File Structure

```
drift_monitoring/
├── app_v1.py           # Main Streamlit application
├── app_cloud.py        # Cloud version with S3 integration
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container configuration
├── snapshots/         # Stored baseline data
└── README.md          # This file
```

## Integration with Main Pipeline

The drift monitoring system integrates with the main ML pipeline by:

1. Reading predictions from S3 buckets
2. Comparing against baseline distributions
3. Alerting when significant drift is detected
4. Generating reports for model retraining decisions

## Deployment

### Kubernetes Deployment

```bash
kubectl apply -f k8s/drift-monitoring-deployment.yml
```

### Environment Variables

```bash
DRIFT_S3_BUCKET=your-bucket-name
AWS_REGION=eu-west-2
MONITORING_FREQUENCY_HOURS=24
```

## Troubleshooting

### Common Issues

1. **S3 Access Denied**: Check AWS credentials and bucket permissions
2. **Memory Issues**: Reduce batch size in configuration
3. **Port Already in Use**: Change port using `--server.port` flag

### Logs

Check application logs:
```bash
kubectl logs -f deployment/drift-monitoring -n loan-prediction-mlops
```

## References

- [Evidently Documentation](https://docs.evidentlyai.com)
- [Streamlit Documentation](https://docs.streamlit.io)