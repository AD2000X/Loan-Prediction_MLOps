# main.py
from fastapi import FastAPI, Request, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
import pandas as pd
import uvicorn
import logging
import io
import os
import time
from datetime import datetime
from prediction_model.predict import generate_predictions, generate_predictions_batch

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="Loan Prediction API",
    description="Serve MLflow models for loan approval prediction with monitoring",
    version="2.0.0",
)

# CORS Configuration
# Allow requests from any origin (modify for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: ["https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Custom Prometheus Metrics
# ============================================================================

# Counter: Total predictions by model version, type, and result
model_predictions_total = Counter(
    'model_predictions_total',
    'Total number of predictions made',
    ['model_version', 'model_type', 'prediction', 'stage']
)

# Histogram: Model loading time
model_load_duration_seconds = Histogram(
    'model_load_duration_seconds',
    'Time taken to load model from MLflow',
    ['model_stage']
)

# Gauge: Batch prediction size
prediction_batch_size = Gauge(
    'prediction_batch_size',
    'Number of samples in batch prediction'
)

# Counter: S3 upload operations
s3_upload_total = Counter(
    's3_upload_total',
    'Total S3 upload operations',
    ['status']  # success or failure
)

# ============================================================================
# Prometheus FastAPI Instrumentator
# Exposes /metrics endpoint automatically for HTTP request metrics
# ============================================================================
Instrumentator().instrument(app).expose(app)

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
def root():
    """
    Root endpoint - API information
    """
    return {
        "message": "Loan Prediction API is running",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "single_prediction": "/prediction_api",
            "batch_prediction": "/batch_prediction",
            "metrics": "/metrics"
        },
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint for Kubernetes liveness/readiness probes
    and monitoring systems
    """
    return {
        "status": "ok",
        "message": "Loan Prediction API is healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/prediction_api")
async def predict_api(request: Request):
    """
    Single prediction endpoint

    Receives a JSON object with loan application features and returns prediction.

    Expected JSON format:
    {
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

    Returns:
    {
        "prediction": "Y" or "N",
        "model_version": "1",
        "model_type": "XGBoost",
        "model_stage": "Production"
    }
    """
    start_time = time.time()
    model_version = None
    model_type = None
    model_stage = None

    try:
        # Parse request
        data = await request.json()
        df = pd.DataFrame([data])

        # Get model stage from query parameter or default to Production
        stage = request.query_params.get("stage", "Production")

        # Generate prediction
        result = generate_predictions(df, stage=stage)

        # Log prediction
        prediction_value = result["prediction"].tolist()[0]
        logger.info(
            f"Prediction: {prediction_value} | "
            f"Model: {result['model_type']} v{result['model_version']} ({result['model_stage']})"
        )

        # Update custom metrics
        model_predictions_total.labels(
            model_version=str(result['model_version']),
            model_type=result['model_type'],
            prediction=prediction_value,
            stage=result['model_stage']
        ).inc()

        return {
            "prediction": prediction_value,
            "model_version": result["model_version"],
            "model_type": result["model_type"],
            "model_stage": result["model_stage"],
            "timestamp": datetime.utcnow().isoformat()
        }

    except KeyError as e:
        logger.error(f"Missing required field: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Missing required field: {e}"
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/batch_prediction")
async def batch_predict_api(
    file: UploadFile = File(...),
    stage: str = "Production",
    upload_to_s3: bool = False,
    s3_bucket: str = None
):
    """
    Batch prediction endpoint

    Accepts a CSV file with multiple loan applications and returns predictions.

    Parameters:
    - file: CSV file with loan application data
    - stage: Model stage to use (Production or Staging), default: Production
    - upload_to_s3: Whether to upload results to S3, default: False
    - s3_bucket: S3 bucket name (required if upload_to_s3=True)

    CSV should contain columns:
    Gender, Married, Dependents, Education, Self_Employed,
    ApplicantIncome, CoapplicantIncome, LoanAmount,
    Loan_Amount_Term, Credit_History, Property_Area

    Returns:
    - CSV file with predictions added as a new column
    - If upload_to_s3=True, also uploads to S3 and returns S3 key
    """
    try:
        # Read uploaded CSV
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        logger.info(f"Batch prediction request: {len(df)} samples, stage={stage}")

        # Update batch size metric
        prediction_batch_size.set(len(df))

        # Generate predictions
        result = generate_predictions_batch(df, stage=stage)

        # Add predictions to dataframe
        df['Loan_Status_Prediction'] = result['prediction']
        df['Model_Version'] = result['model_version']
        df['Model_Type'] = result['model_type']

        # Update metrics for each prediction
        for pred in result['prediction']:
            model_predictions_total.labels(
                model_version=str(result['model_version']),
                model_type=result['model_type'],
                prediction=pred,
                stage=result['model_stage']
            ).inc()

        logger.info(
            f"Batch prediction completed: {len(df)} samples | "
            f"Model: {result['model_type']} v{result['model_version']}"
        )

        # Convert to CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        # Upload to S3 if requested
        s3_key = None
        if upload_to_s3:
            if not s3_bucket:
                raise HTTPException(
                    status_code=400,
                    detail="s3_bucket parameter required when upload_to_s3=True"
                )

            try:
                import boto3
                s3_client = boto3.client('s3')

                # Generate S3 key with timestamp
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                s3_key = f"predictions/batch_prediction_{timestamp}.csv"

                # Upload
                s3_client.put_object(
                    Bucket=s3_bucket,
                    Key=s3_key,
                    Body=output.getvalue().encode('utf-8'),
                    ContentType='text/csv'
                )

                logger.info(f"Uploaded results to s3://{s3_bucket}/{s3_key}")
                s3_upload_total.labels(status='success').inc()

            except Exception as e:
                logger.error(f"S3 upload failed: {e}")
                s3_upload_total.labels(status='failure').inc()
                # Continue execution - still return CSV even if S3 upload fails

        # Reset buffer for response
        output.seek(0)

        # Prepare response headers
        headers = {
            'Content-Disposition': f'attachment; filename="predictions_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv"',
            'X-Model-Version': str(result['model_version']),
            'X-Model-Type': result['model_type'],
            'X-Model-Stage': result['model_stage'],
            'X-Batch-Size': str(len(df))
        }

        if s3_key:
            headers['X-S3-Key'] = s3_key
            headers['X-S3-Bucket'] = s3_bucket

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers=headers
        )

    except pd.errors.EmptyDataError:
        logger.error("Uploaded file is empty")
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty")

    except pd.errors.ParserError as e:
        logger.error(f"CSV parsing error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {e}")

    except Exception as e:
        logger.error(f"Batch prediction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch prediction failed: {str(e)}"
        )


@app.get("/model_info")
def get_model_info(stage: str = "Production"):
    """
    Get information about the currently deployed model

    Parameters:
    - stage: Model stage (Production or Staging), default: Production

    Returns model metadata including version, type, and metrics
    """
    try:
        from prediction_model.predict import ModelLoader

        loader = ModelLoader()
        info = loader.get_model_info(stage)

        if "error" in info:
            raise HTTPException(status_code=404, detail=info["error"])

        return info

    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list_models")
def list_all_models():
    """
    List all available model versions in MLflow Registry

    Returns list of all model versions with their metadata
    """
    try:
        from prediction_model.predict import ModelLoader

        loader = ModelLoader()
        versions = loader.list_all_versions()

        return {
            "total_versions": len(versions),
            "models": versions
        }

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Application Startup
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Run on application startup
    """
    logger.info("="*60)
    logger.info("Loan Prediction API Starting...")
    logger.info(f"Version: 2.0.0")
    logger.info(f"MLflow Tracking URI: {os.getenv('MLFLOW_TRACKING_URI', 'Not configured')}")
    logger.info("="*60)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on application shutdown
    """
    logger.info("Loan Prediction API shutting down...")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8005,
        log_level="info"
    )
