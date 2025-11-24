import pathlib
import os
import mlflow

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent # .../prediction_model
PROJECT_ROOT = PACKAGE_ROOT.parent # .../Loan-Prediction_MLOps

DATAPATH = PROJECT_ROOT / "datasets"

# MLflow Tracking Configuration
# Note: MLflow tracking backend must be file:// or database URI (not S3)
# S3 is used only for artifact storage
S3_BUCKET = "loanpred-mlops-20251118-120330"
MLRUNS_PATH = PROJECT_ROOT / "mlruns"

# Always use local file-based tracking URI with relative path for portability
# Why: Relative paths work across different environments without path issues
# Artifacts will be stored in S3 when AWS credentials are available
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "./mlruns")
mlflow.set_tracking_uri(TRACKING_URI)

# Configure S3 artifact storage for production
# MLflow will automatically use S3 for artifacts when default_artifact_root is set
if os.getenv("AWS_EXECUTION_ENV") or os.getenv("GITHUB_ACTIONS"):
    # Production: use S3 for artifact storage
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = "https://s3.eu-west-2.amazonaws.com"
    ARTIFACT_ROOT = f"s3://{S3_BUCKET}/mlartifacts"
else:
    # Development: use local storage
    ARTIFACT_ROOT = None

# Dataset configuration
TRAIN_FILE = 'train.csv'
TEST_FILE = 'test.csv'

TARGET = 'Loan_Status'

# Feature configuration
FEATURES = ['Gender', 'Married', 'Dependents', 'Education',
       'Self_Employed', 'ApplicantIncome', 'CoapplicantIncome', 'LoanAmount',
       'Loan_Amount_Term', 'Credit_History', 'Property_Area']

NUM_FEATURES = ['ApplicantIncome', 'LoanAmount', 'Loan_Amount_Term']

CAT_FEATURES = ['Gender',
 'Married',
 'Dependents',
 'Education',
 'Self_Employed',
 'Credit_History',
 'Property_Area']

FEATURES_TO_ENCODE = ['Gender',
 'Married',
 'Dependents',
 'Education',
 'Self_Employed',
 'Credit_History',
 'Property_Area']

FEATURE_TO_MODIFY = ['ApplicantIncome']
FEATURE_TO_ADD = 'CoapplicantIncome'

DROP_FEATURES = ['CoapplicantIncome']

LOG_FEATURES = ['ApplicantIncome', 'LoanAmount']

# Data drift monitoring
FOLDER = "datadrift"

# MLflow experiment configuration
EXPERIMENT_NAME = "loan_prediction_model"
MODEL_NAME = "/Loanprediction-model"

# Model performance thresholds for quality gates
MIN_F1_SCORE = 0.85
MIN_ACCURACY = 0.80
MIN_RECALL = 0.80
MIN_PRECISION = 0.75

