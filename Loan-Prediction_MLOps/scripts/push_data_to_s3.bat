@echo off
REM Script to push datasets to S3 via DVC (Windows)
REM Usage: scripts\push_data_to_s3.bat

echo ========================================
echo DVC Data Push to S3
echo ========================================

REM Check if DVC is installed
where dvc >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: DVC is not installed
    echo Install with: pip install dvc[s3]
    exit /b 1
)

REM Check AWS credentials
echo Checking AWS credentials...
aws sts get-caller-identity >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: AWS credentials not configured
    echo Run: aws configure
    exit /b 1
)

echo AWS Identity:
aws sts get-caller-identity

REM Check if datasets directory exists
if not exist "datasets" (
    echo Error: datasets\ directory not found
    exit /b 1
)

echo.
echo Datasets found:
dir datasets

REM DVC add
echo.
echo Tracking datasets with DVC...
dvc add datasets

REM Show DVC status
echo.
echo DVC Status:
dvc status

REM Push to S3
echo.
echo Pushing datasets to S3...
dvc push -v

echo.
echo ========================================
echo Success! Data pushed to S3
echo ========================================
echo.
echo Next steps:
echo 1. git add datasets.dvc .gitignore
echo 2. git commit -m "Update datasets"
echo 3. git push
echo.
echo S3 Location: s3://loanpred-mlops-20251103/
echo ========================================
