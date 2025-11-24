@echo off
REM Local Docker Build Script for Windows
REM Usage: scripts\build_docker_local.bat

echo ========================================
echo Local Docker Image Build
echo ========================================

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Docker is not running
    echo Please start Docker Desktop
    exit /b 1
)

REM Check if mlruns exists
if not exist "mlruns" (
    echo Warning: mlruns/ directory not found
    echo.
    echo You need to train the model first:
    echo   python -m prediction_model.training_pipeline
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "%CONTINUE%"=="y" exit /b 1
)

echo.
echo Building Docker image...
echo Tag: loan-prediction:local
echo.

REM Build Docker image
docker build -t loan-prediction:local .

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Success! Docker image built
    echo ========================================
    echo.
    echo Image: loan-prediction:local
    docker images | findstr loan-prediction
    echo.
    echo To run the container:
    echo   docker run -d -p 8005:8005 --name loan-pred loan-prediction:local
    echo.
    echo To test:
    echo   curl http://localhost:8005/health
    echo.
) else (
    echo.
    echo ========================================
    echo Build failed!
    echo ========================================
    exit /b 1
)
