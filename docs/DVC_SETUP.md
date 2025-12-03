# DVC (Data Version Control) Setup Guide

## Overview

This project uses DVC to version control datasets and sync them with AWS S3, ensuring reproducible ML workflows.

## Configuration

### DVC Remote Storage
- **S3 Bucket**: `s3://loanpred-mlops-20251118-120330`
- **Region**: `eu-west-2`
- **Remote Name**: `myremote`

## Initial Setup (One-time)

### 1. Install DVC

```bash
pip install dvc[s3]
```

### 2. Verify DVC Configuration

```bash
# Check DVC version
dvc version

# View DVC configuration
cat .dvc/config

# View tracked datasets
cat datasets.dvc
```

## Daily Workflow

### Pushing Data to S3 (After updating datasets)

```bash
# 1. Track new or updated datasets
dvc add datasets/

# 2. Push data to S3
dvc push

# 3. Commit the .dvc file (NOT the actual data)
git add datasets.dvc .dvc/
git commit -m "Update datasets"
git push
```

### Pulling Data from S3 (Fresh clone or sync)

```bash
# Pull the latest datasets from S3
dvc pull

# Verify datasets are present
ls -lh datasets/
```

## CI/CD Integration

The GitHub Actions workflow automatically:

1. **On Push to main/develop**:
   - Pulls data from S3 via DVC
   - Trains models with the latest data
   - Pushes MLflow artifacts to S3
   - Builds and deploys Docker image

2. **Data Sync Flow**:
```
GitHub Actions
    dvc pull (download datasets from S3)
    train models
    sync mlruns to s3://loanpred-mlops-20251118-120330/mlruns/
    deploy to EKS
```

## AWS Credentials

DVC uses the same AWS credentials as the rest of the project:

- **In CI/CD**: OIDC authentication via GitHub Actions
- **Locally**: AWS CLI credentials (`~/.aws/credentials`)

### Setup AWS CLI (Local)

```bash
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: eu-west-2
# - Default output format: json
```

## File Structure

```
project_root/
  datasets/               # Actual data (gitignored)
    train.csv
    test.csv
  datasets.dvc            # DVC metadata (tracked in git)
  .dvc/                   # DVC configuration
    config
    .gitignore
  .dvcignore              # DVC ignore list
```


## Common Commands

### Check Status
```bash
dvc status          # Check if data is in sync
dvc diff            # Show data changes
```

### Data Management
```bash
dvc pull            # Download data from S3
dvc push            # Upload data to S3
dvc fetch           # Download to cache without checking out
dvc checkout        # Checkout data from cache
```

### Remote Management
```bash
dvc remote list                                    # List remotes
dvc remote modify myremote region eu-west-2        # Modify remote config
```

## Troubleshooting

### "No remote configured"
```bash
# Add the remote
dvc remote add -d myremote s3://loanpred-mlops-20251118-120330
dvc remote modify myremote region eu-west-2
```

### "Access Denied" when pushing/pulling
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check S3 bucket access
aws s3 ls s3://loanpred-mlops-20251118-120330/
```

### Data out of sync
```bash
# Force pull to overwrite local data
dvc pull --force

# Or reset to match .dvc file
dvc checkout --force
```

## Best Practices

1. **Never commit large datasets to Git** - Always use DVC
2. **Commit `.dvc` files to Git** - These are small metadata files
3. **Run `dvc push` after updating data** - Keep S3 in sync
4. **Run `dvc pull` after cloning** - Get the latest data
5. **Use meaningful commit messages** - Describe data changes

## Workflow Example

### Adding New Training Data

```bash
# 1. Add new data files to datasets/
cp new_data.csv datasets/

# 2. Track with DVC
dvc add datasets/

# 3. Push to S3
dvc push

# 4. Commit metadata
git add datasets.dvc .gitignore
git commit -m "Add new training data from Q4 2024"
git push

# 5. CI/CD will automatically pull and retrain
```

### Team Collaboration

```bash
# Developer A: Updates data
dvc add datasets/
dvc push
git add datasets.dvc
git commit -m "Update training data"
git push

# Developer B: Gets latest
git pull
dvc pull  # Downloads the updated datasets
```

## Monitoring

### Check Data Version
```bash
# See what version of data is tracked
git log --oneline datasets.dvc

# View specific version
git show <commit-hash>:datasets.dvc
```

### S3 Storage Usage
```bash
# Check S3 bucket size
aws s3 ls s3://loanpred-mlops-20251118-120330/ --recursive --human-readable --summarize
```

## Integration with MLflow

The workflow now syncs both:
- **Datasets** via DVC → S3
- **MLflow artifacts** (models, metrics) → S3

```
s3://loanpred-mlops-20251118-120330/
├── .dvc/               # DVC cache
├── mlruns/             # MLflow experiments
└── datadrift/          # Drift monitoring data
```

## Next Steps

After setting up DVC:

1. Data is versioned and backed up to S3
2. CI/CD automatically pulls latest data
3. Models are trained on consistent datasets
4. Full reproducibility of ML pipeline

For questions or issues, check the [DVC documentation](https://dvc.org/doc) or contact the ML team.
