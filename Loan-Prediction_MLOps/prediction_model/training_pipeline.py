import os
import pathlib
os.environ['MPLBACKEND'] = 'Agg' # Use Agg backend for non-GUI environments

import matplotlib
matplotlib.use('Agg')

import warnings
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient

# Scikit-learn
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    f1_score, accuracy_score, recall_score, precision_score
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler

# Hyperparameter Optimization
from hyperopt import fmin, tpe, hp, Trials, STATUS_OK

# Models
import xgboost as xgb
import lightgbm as lgb

# Explainability & Fairness
import shap 
from fairlearn.metrics import MetricFrame, true_positive_rate, equalized_odds_difference

# Custom Module Imports
from prediction_model.config import config
# Using Code 2's data_handling path
from prediction_model.processing.data_handling import load_dataset 
import prediction_model.processing.preprocessing as pp 


# Initial Setup
warnings.filterwarnings("ignore")

# ========================================
# MLflow Configuration with Absolute Paths
# ========================================
# Get absolute path for MLflow tracking
import platform

if os.getenv("MLFLOW_TRACKING_URI"):
    # If set in environment, use it but ensure it's absolute
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if tracking_uri.startswith("file:"):
        # Convert relative file:// URI to absolute
        if tracking_uri.startswith("file:./") or tracking_uri.startswith("file:mlruns"):
            # Get workspace root for CI environment
            workspace = os.getenv("GITHUB_WORKSPACE")
            if workspace:
                mlruns_path = os.path.join(workspace, "mlruns")
            else:
                # Local development
                mlruns_path = os.path.abspath("mlruns")

            # Format URI based on OS
            if platform.system() == "Windows":
                # Windows: use file:/// with forward slashes
                mlruns_path_fixed = mlruns_path.replace("\\", "/")
                tracking_uri = f"file:///{mlruns_path_fixed}"
            else:
                # Unix: use file://
                tracking_uri = f"file://{mlruns_path}"
else:
    # Use absolute path based on project root
    mlruns_path = config.MLRUNS_PATH.resolve()

    # Format URI based on OS
    if platform.system() == "Windows":
        # Windows: use file:/// with forward slashes
        mlruns_path_str = str(mlruns_path).replace("\\", "/")
        tracking_uri = f"file:///{mlruns_path_str}"
    else:
        # Unix: use file://
        tracking_uri = f"file://{mlruns_path}"

print(f"[MLflow Setup] Tracking URI: {tracking_uri}")
mlflow.set_tracking_uri(tracking_uri)
print(f"[MLflow Setup] Active tracking URI: {mlflow.get_tracking_uri()}")

# Set experiment name BEFORE any runs
EXPERIMENT_NAME = "loan_prediction_model"
# Always set the experiment first
mlflow.set_experiment(EXPERIMENT_NAME)
experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
if experiment:
    print(f"[MLflow Setup] Active experiment: {experiment.name} (ID: {experiment.experiment_id})")
    print(f"[MLflow Setup] Artifact location: {experiment.artifact_location}")
else:
    print(f"[MLflow Setup] Creating new experiment: {EXPERIMENT_NAME}")
    if config.ARTIFACT_ROOT:
        try:
            experiment_id = mlflow.create_experiment(
                EXPERIMENT_NAME,
                artifact_location=config.ARTIFACT_ROOT
            )
        except Exception as e:
            print(f"Warning: Could not set S3 artifact location: {e}")
            experiment_id = mlflow.create_experiment(EXPERIMENT_NAME)
    else:
        experiment_id = mlflow.create_experiment(EXPERIMENT_NAME)
    experiment = mlflow.get_experiment(experiment_id)

# Debug: List all experiments to verify
print("\n[MLflow Debug] All experiments:")
for exp in mlflow.search_experiments():
    run_count = len(mlflow.search_runs(experiment_ids=[exp.experiment_id], max_results=1))
    print(f"  - {exp.name} (ID: {exp.experiment_id}) - Has runs: {run_count > 0}")

# Model Registry name
MODEL_REGISTRY_NAME = "LoanPrediction"


def get_data(input_file):
    """
    Load and prepare training data.
    Maps target variable to binary (0/1).
    
    Args:
        input_file: filename of the training data
    
    Returns:
        X: features dataframe
        Y: target series (binary: 0 or 1)
    """
    data = load_dataset(input_file)
    X = data[config.FEATURES]
    Y = data[config.TARGET].map({'N': 0, 'Y': 1})
    return X, Y


# Load and split data globally for all trials
X, Y = get_data(config.TRAIN_FILE)
X_train, X_test, y_train, y_test = train_test_split(
    X, Y, test_size=0.2, random_state=42, stratify=Y
)


# XGBoost Configuration
xgboost_search_space = {
    'max_depth': hp.quniform('xgb_max_depth', 3, 10, 1),
    'learning_rate': hp.uniform('xgb_learning_rate', 0.01, 0.3),
    'n_estimators': hp.quniform('xgb_n_estimators', 50, 300, 50),
    'subsample': hp.uniform('xgb_subsample', 0.5, 1.0),
    'colsample_bytree': hp.uniform('xgb_colsample_bytree', 0.5, 1.0),
    'gamma': hp.uniform('xgb_gamma', 0, 5),
    'reg_alpha': hp.uniform('xgb_reg_alpha', 0, 1),
    'reg_lambda': hp.uniform('xgb_reg_lambda', 0, 1)
}


def objective_xgboost(params):
    """
    Objective function for XGBoost HPO.
    Includes MLflow logging for metrics, SHAP, and Fairlearn.
    
    Args:
        params: dictionary of hyperparameters from search space
    
    Returns:
        dict: loss (1 - f1_score) and status for Hyperopt
    """
    # Create XGBoost classifier (convert quniform floats to ints)
    clf = xgb.XGBClassifier(
        max_depth=int(params['max_depth']),
        learning_rate=params['learning_rate'],
        n_estimators=int(params['n_estimators']),
        subsample=params['subsample'],
        colsample_bytree=params['colsample_bytree'],
        gamma=params['gamma'],
        reg_alpha=params['reg_alpha'],
        reg_lambda=params['reg_lambda'],
        use_label_encoder=False,
        eval_metric='logloss',
        random_state=42
    )
    
    # Build complete preprocessing and model pipeline
    classification_pipeline = Pipeline([
        ('DomainProcessing', pp.DomainProcessing(
            variable_to_modify=config.FEATURE_TO_MODIFY,
            variable_to_add=config.FEATURE_TO_ADD
        )),
        ('MeanImputation', pp.MeanImputer(variables=config.NUM_FEATURES)),
        ('ModeImputation', pp.ModeImputer(variables=config.CAT_FEATURES)),
        ('DropFeatures', pp.DropColumns(variables_to_drop=config.DROP_FEATURES)),
        ('LabelEncoder', pp.CustomLabelEncoder(variables=config.FEATURES_TO_ENCODE)),
        ('LogTransform', pp.LogTransforms(variables=config.LOG_FEATURES)),
        ('MinMaxScale', MinMaxScaler()),
        ('XGBoostClassifier', clf) # Model step name
    ])
    classification_pipeline.set_output(transform="pandas")

    # Enable MLflow autologging for XGBoost
    mlflow.xgboost.autolog()

    # Start MLflow run
    try:
        with mlflow.start_run(nested=True, run_name="XGBoost_Trial") as run:
            print(f"Started nested run: {run.info.run_id}")

            # Train
            classification_pipeline.fit(X_train, y_train)

            # Predict
            y_pred = classification_pipeline.predict(X_test)

            # --- Standard Metrics (From Code 2) ---
            f1 = f1_score(y_test, y_pred)
            accuracy = accuracy_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)

            mlflow.log_metrics({
                'f1_score': f1,
                'accuracy': accuracy,
                'recall': recall,
                'precision': precision
            })

            # SHAP Explanation
            try:
                # Get the fitted model
                model = classification_pipeline.named_steps['XGBoostClassifier']

                # Create a new pipeline containing *only* the fitted preprocessor steps
                preprocessor_pipeline = Pipeline(classification_pipeline.steps[:-1])

                # --- THE FIX ---
                # Tell this preprocessor pipeline to output Pandas DataFrames
                # This requires scikit-learn 1.2+
                try:
                    preprocessor_pipeline.set_output(transform="pandas")
                except AttributeError:
                    print("SHAP Warning: scikit-learn < 1.2. Cannot set output to pandas. "
                          "Feature names might be lost.")
                except Exception as e:
                     print(f"SHAP Warning: Could not set output to pandas: {e}")
                # --- END FIX ---

                # Transform test data.
                # If set_output worked, this is a DataFrame with column names.
                X_test_transformed = preprocessor_pipeline.transform(X_test)

                feature_names = None
                # Check if the output is a DataFrame (new method)
                if hasattr(X_test_transformed, 'columns'):
                    feature_names = X_test_transformed.columns.tolist()
                else:
                    # Try the old method (get_feature_names_out) as a fallback
                    try:
                        feature_names = preprocessor_pipeline.get_feature_names_out()
                    except Exception:
                        print("SHAP Warning: Could not get feature names from preprocessor.")
                        feature_names = None # Will default to f0, f1...

                explainer = shap.Explainer(model)
                shap_values = explainer(X_test_transformed)

                # Plot and log SHAP summary
                plt.figure()

                # Pass the transformed data (which might be a DF) and the explicit names
                # If X_test_transformed is a DataFrame, SHAP will use its column names
                shap.summary_plot(shap_values, X_test_transformed, show=False, feature_names=feature_names)

                shap_path = f"shap_summary_{run.info.run_id}.png"
                plt.savefig(shap_path, bbox_inches='tight')
                mlflow.log_artifact(shap_path)
                plt.close() # Close plot to free memory

            except Exception as e:
                print(f"SHAP error: {e}")

            # Fairlearn Metrics
            try:
                sensitive_feature_name = "Gender"
                if sensitive_feature_name in X_test.columns:
                    sensitive_feature_series = X_test[sensitive_feature_name]

                    # FIX: Fill missing values (NaNs) which are floats,
                    # causing the 'str' vs 'float' comparison error.
                    # We fill with a string 'Unknown' to keep the type consistent.
                    sensitive_feature = sensitive_feature_series.fillna("Unknown")

                    # MetricFrame for True Positive Rate (TPR)
                    frame = MetricFrame(
                        metrics={"TPR": true_positive_rate},
                        y_true=y_test,
                        y_pred=y_pred,
                        sensitive_features=sensitive_feature # Use the filled series
                    )
                    tpr_disparity = frame.difference(method="between_groups")
                    mlflow.log_metric("TPR_disparity", tpr_disparity)

                    # Equalized Odds Difference (combines TPR and FPR disparity)
                    eo_diff = equalized_odds_difference(
                        y_true=y_test,
                        y_pred=y_pred,
                        sensitive_features=sensitive_feature # Use the filled series
                    )
                    mlflow.log_metric("Equalized_Odds_Diff", eo_diff)
                else:
                    print(f"Sensitive feature '{sensitive_feature_name}' not in X_test. Skipping Fairlearn.")

            except Exception as e:
                print(f"Fairlearn error: {e}")

            # Model Logging
            mlflow.set_tag("model_type", "xgboost")
            mlflow.set_tag("training_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Log the complete pipeline
            mlflow.sklearn.log_model(
                classification_pipeline,
                "Loanprediction-model",
                registered_model_name=None
            )

    except Exception as e:
        print(f"MLflow run error in XGBoost objective: {e}")
        # Return a penalty score if run fails
        return {'loss': 1.0, 'status': STATUS_OK}

    # Return loss for Hyperopt
    return {'loss': 1 - f1, 'status': STATUS_OK}


# LightGBM Configuration
lightgbm_search_space = {
    'max_depth': hp.quniform('lgb_max_depth', 3, 10, 1),
    'learning_rate': hp.uniform('lgb_learning_rate', 0.01, 0.3),
    'n_estimators': hp.quniform('lgb_n_estimators', 50, 300, 50),
    'subsample': hp.uniform('lgb_subsample', 0.5, 1.0),
    'colsample_bytree': hp.uniform('lgb_colsample_bytree', 0.5, 1.0),
    'reg_alpha': hp.uniform('lgb_reg_alpha', 0, 1),
    'reg_lambda': hp.uniform('lgb_reg_lambda', 0, 1),
    'min_child_samples': hp.quniform('lgb_min_child_samples', 5, 50, 5),
    'num_leaves': hp.quniform('lgb_num_leaves', 20, 100, 10)
}


def objective_lightgbm(params):
    """
    Objective function for LightGBM HPO.
    Includes MLflow logging for metrics, SHAP, and Fairlearn.
    
    Args:
        params: dictionary of hyperparameters from search space
    
    Returns:
        dict: loss (1 - f1_score) and status for Hyperopt
    """
    # Create LightGBM classifier (convert quniform floats to ints)
    clf = lgb.LGBMClassifier(
        max_depth=int(params['max_depth']),
        learning_rate=params['learning_rate'],
        n_estimators=int(params['n_estimators']),
        subsample=params['subsample'],
        colsample_bytree=params['colsample_bytree'],
        reg_alpha=params['reg_alpha'],
        reg_lambda=params['reg_lambda'],
        min_child_samples=int(params['min_child_samples']),
        num_leaves=int(params['num_leaves']),
        random_state=42,
        verbose=-1 
    )
    
    # Build complete preprocessing and model pipeline
    classification_pipeline = Pipeline([
        ('DomainProcessing', pp.DomainProcessing(
            variable_to_modify=config.FEATURE_TO_MODIFY,
            variable_to_add=config.FEATURE_TO_ADD
        )),
        ('MeanImputation', pp.MeanImputer(variables=config.NUM_FEATURES)),
        ('ModeImputation', pp.ModeImputer(variables=config.CAT_FEATURES)),
        ('DropFeatures', pp.DropColumns(variables_to_drop=config.DROP_FEATURES)),
        ('LabelEncoder', pp.CustomLabelEncoder(variables=config.FEATURES_TO_ENCODE)),
        ('LogTransform', pp.LogTransforms(variables=config.LOG_FEATURES)),
        ('MinMaxScale', MinMaxScaler()),
        ('LightGBMClassifier', clf) # Model step name
    ])
    classification_pipeline.set_output(transform="pandas")
    
    # Enable MLflow autologging
    mlflow.lightgbm.autolog()
    
    # Start MLflow run
    with mlflow.start_run(nested=True, run_name="LightGBM_Trial") as run:
        # Train
        classification_pipeline.fit(X_train, y_train)
        
        # Predict
        y_pred = classification_pipeline.predict(X_test)
        
        # --- Standard Metrics (From Code 2) ---
        f1 = f1_score(y_test, y_pred)
        accuracy = accuracy_score(y_test, y_pred)
        recall = recall_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred)
        
        mlflow.log_metrics({
            'f1_score': f1,
            'accuracy': accuracy,
            'recall': recall,
            'precision': precision
        })
        
        # SHAP Explanation
        try:
            # Get the fitted model
            model = classification_pipeline.named_steps['LightGBMClassifier']
            
            # Create a new pipeline containing *only* the fitted preprocessor steps
            preprocessor_pipeline = Pipeline(classification_pipeline.steps[:-1])
            
            # Tell this preprocessor pipeline to output Pandas DataFrames
            try:
                preprocessor_pipeline.set_output(transform="pandas")
            except AttributeError:
                print("SHAP Warning: scikit-learn < 1.2. Cannot set output to pandas. "
                      "Feature names might be lost.")
            except Exception as e:
                 print(f"SHAP Warning: Could not set output to pandas: {e}")

            # Transform test data. 
            X_test_transformed = preprocessor_pipeline.transform(X_test) 
            
            feature_names = None
            # Check if the output is a DataFrame (new method)
            if hasattr(X_test_transformed, 'columns'):
                feature_names = X_test_transformed.columns.tolist()
            else:
                # Try the old method (get_feature_names_out) as a fallback
                try:
                    feature_names = preprocessor_pipeline.get_feature_names_out()
                except Exception:
                    print("SHAP Warning: Could not get feature names from preprocessor.")
                    feature_names = None # Will default to f0, f1...

            explainer = shap.Explainer(model)
            shap_values = explainer(X_test_transformed)

            if isinstance(shap_values, list):
                shap_to_plot = shap_values[1] if len(shap_values) > 1 else shap_values[0]
            elif hasattr(shap_values, "values"):
                shap_array = shap_values.values
                if shap_array.ndim == 3:
                    class_idx = min(1, shap_array.shape[2] - 1)  # choose positive class if present
                    shap_to_plot = shap_array[:, :, class_idx]   # keep (n_samples, n_features)
                else:
                    shap_to_plot = shap_array

            shap.summary_plot(shap_to_plot, X_test_transformed, show=False, feature_names=feature_names)
            
            shap_path = f"shap_summary_{run.info.run_id}.png"
            plt.savefig(shap_path, bbox_inches='tight')
            mlflow.log_artifact(shap_path)
            plt.close() # Close plot to free memory
            
        except Exception as e:
            print(f"SHAP error: {e}")

        # Fairlearn Metrics
        try:
            sensitive_feature_name = "Gender"
            if sensitive_feature_name in X_test.columns:
                sensitive_feature_series = X_test[sensitive_feature_name]
                
                # Fill missing values (NaNs) which are floats
                sensitive_feature = sensitive_feature_series.fillna("Unknown") 

                frame = MetricFrame(
                    metrics={"TPR": true_positive_rate},
                    y_true=y_test,
                    y_pred=y_pred,
                    sensitive_features=sensitive_feature # Use the filled series
                )
                tpr_disparity = frame.difference(method="between_groups")
                mlflow.log_metric("TPR_disparity", tpr_disparity)

                eo_diff = equalized_odds_difference(
                    y_true=y_test, 
                    y_pred=y_pred, 
                    sensitive_features=sensitive_feature # Use the filled series
                )
                mlflow.log_metric("Equalized_Odds_Diff", eo_diff)
            else:
                 print(f"Sensitive feature '{sensitive_feature_name}' not in X_test. Skipping Fairlearn.")

        except Exception as e:
            print(f"Fairlearn error: {e}")

        # Model Logging
        mlflow.set_tag("model_type", "lightgbm")
        mlflow.set_tag("training_date", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        mlflow.sklearn.log_model(
            classification_pipeline,
            "Loanprediction-model",
            registered_model_name=None 
        )
    
    # Return loss for Hyperopt
    return {'loss': 1 - f1, 'status': STATUS_OK}


# MLOps/Registry Functions
def train_and_register_model(model_type="xgboost", stage="Staging", max_evals=5):
    """
    Train model with HPO and register to MLflow Model Registry.
    
    Args:
        model_type: "xgboost" or "lightgbm"
        stage: MLflow Model Registry stage ("Staging" or "Production")
        max_evals: number of HPO trials
    
    Returns:
        best_params: dictionary of best hyperparameters found
        best_run_id: MLflow run ID of the best model
        model_version: version number in Model Registry
    """
    print(f"\n{'='*60}")
    print(f"Training {model_type.upper()} model...")
    print(f"{'='*60}\n")
    
    # Select search space and objective function
    if model_type.lower() == "xgboost":
        search_space = xgboost_search_space
        objective_fn = objective_xgboost
    elif model_type.lower() == "lightgbm":
        search_space = lightgbm_search_space
        objective_fn = objective_lightgbm
    else:
        raise ValueError("model_type must be 'xgboost' or 'lightgbm'")
    
    # Start parent MLflow run for the HPO process
    with mlflow.start_run(run_name=f"{model_type.upper()}_Optimization") as parent_run:

        mlflow.log_params({
            "model_type": model_type,
            "max_evals": max_evals,
            "test_size": 0.2,
            "random_state": 42
        })

        # Set tag for searchability
        mlflow.set_tag("model_type", model_type)

        trials = Trials()
        
        # Run HPO
        best_params = fmin(
            fn=objective_fn,
            space=search_space,
            algo=tpe.suggest,
            max_evals=max_evals,
            trials=trials,
            verbose=1,
            show_progressbar=False
        )
        
        print(f"\nBest hyperparameters for {model_type.upper()}: {best_params}\n")
        mlflow.log_params({"best_" + k: v for k, v in best_params.items()})
    
    # Get experiment details
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    experiment_id = experiment.experiment_id

    # Use MlflowClient to search for child runs
    client = MlflowClient()

    print(f"\n[Search] Looking for child runs of parent: {parent_run.info.run_id}")
    print(f"[Search] Primary experiment ID: {experiment_id}")

    # First try: Search in the current experiment
    try:
        all_runs = client.search_runs(
            experiment_ids=[experiment_id],
            max_results=1000,
            order_by=["metrics.f1_score DESC"]
        )

        print(f"[Search] Total runs in primary experiment: {len(all_runs)}")

        # Filter for child runs of this parent
        child_runs = [
            run for run in all_runs
            if run.data.tags.get("mlflow.parentRunId") == parent_run.info.run_id
            and run.data.metrics.get("f1_score") is not None
        ]

        print(f"[Search] Found {len(child_runs)} child runs in primary experiment")

    except Exception as e:
        print(f"Warning: Error searching in primary experiment: {e}")
        child_runs = []

    # If no child runs found, search across ALL experiments
    if len(child_runs) == 0:
        print("\n[Search] No child runs in primary experiment. Searching ALL experiments...")

        try:
            # Get all experiment IDs
            all_experiments = mlflow.search_experiments()
            all_exp_ids = [exp.experiment_id for exp in all_experiments]

            print(f"[Search] Searching across {len(all_exp_ids)} experiments: {[exp.name for exp in all_experiments]}")

            # Search across all experiments
            all_runs = client.search_runs(
                experiment_ids=all_exp_ids,
                filter_string=f'tags.mlflow.parentRunId = "{parent_run.info.run_id}"',
                max_results=5000,
                order_by=["metrics.f1_score DESC"]
            )

            print(f"[Search] Found {len(all_runs)} child runs across all experiments")

            # Filter for valid runs with metrics
            child_runs = [
                run for run in all_runs
                if run.data.metrics.get("f1_score") is not None
            ]

            print(f"[Search] {len(child_runs)} child runs have f1_score metrics")

            # Debug: Show which experiments contain runs
            if len(all_runs) > 0:
                run_experiments = {}
                for run in all_runs:
                    exp_id = run.info.experiment_id
                    if exp_id not in run_experiments:
                        run_experiments[exp_id] = 0
                    run_experiments[exp_id] += 1

                print("\n[Search Debug] Runs found in experiments:")
                for exp_id, count in run_experiments.items():
                    exp_name = next((e.name for e in all_experiments if e.experiment_id == exp_id), "Unknown")
                    print(f"  - {exp_name} (ID: {exp_id}): {count} runs")

        except Exception as e:
            print(f"Warning: Error searching across all experiments: {e}")
            import traceback
            traceback.print_exc()
            child_runs = []

    # Final check and debug info
    if len(child_runs) == 0:
        print(f"\n[Search Failed] No child runs found for parent {parent_run.info.run_id}")
        print("[Debug] Checking if runs exist at all...")

        # List ANY runs in the tracking store
        try:
            any_runs = client.search_runs(
                experiment_ids=[exp.experiment_id for exp in mlflow.search_experiments()],
                max_results=10
            )
            print(f"[Debug] Total runs in tracking store: {len(any_runs)}")
            if len(any_runs) > 0:
                print("[Debug] Sample runs:")
                for i, run in enumerate(any_runs[:5]):
                    parent_id = run.data.tags.get("mlflow.parentRunId", "None")
                    exp_id = run.info.experiment_id
                    print(f"  Run {i}: exp={exp_id}, parent={parent_id[:8] if parent_id != 'None' else 'None'}, status={run.info.status}")
        except:
            pass

        raise ValueError(
            f"No valid child runs found during hyperparameter optimization. "
            f"Parent run ID: {parent_run.info.run_id}. "
            f"Tracking URI: {mlflow.get_tracking_uri()}. "
            f"This indicates the nested runs were not properly saved. "
            f"Please check that the MLflow tracking directory is writable."
        )

    # Get best run (first in the sorted list)
    best_run = child_runs[0]
    best_run_id = best_run.info.run_id
    best_f1_score = best_run.data.metrics.get('f1_score', 0.0)
    best_accuracy = best_run.data.metrics.get('accuracy', 0.0)
    best_recall = best_run.data.metrics.get('recall', 0.0)
    best_precision = best_run.data.metrics.get('precision', 0.0)

    print(f"\nBest {model_type.upper()} model:")
    print(f"  - Run ID: {best_run_id}")
    print(f"  - F1 Score: {best_f1_score:.4f}")
    print(f"  - Accuracy: {best_accuracy:.4f}")
    print(f"  - Recall: {best_recall:.4f}")
    print(f"  - Precision: {best_precision:.4f}\n")
    
    # Register the best model
    model_uri = f"runs:/{best_run_id}/Loanprediction-model"
    # Reuse client from above
    
    try:
        registered_model = mlflow.register_model(
            model_uri=model_uri,
            name=MODEL_REGISTRY_NAME,
            tags={
                "model_type": model_type,
                "f1_score": str(best_f1_score),
                "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        model_version = registered_model.version
        print(f"Model registered as '{MODEL_REGISTRY_NAME}' version {model_version}")
    except Exception as e:
        print(f"Error registering model: {e}")
        latest_versions = client.get_latest_versions(MODEL_REGISTRY_NAME)
        model_version = latest_versions[-1].version if latest_versions else "1"
    
    # Transition model to specified stage
    try:
        client.transition_model_version_stage(
            name=MODEL_REGISTRY_NAME,
            version=model_version,
            stage=stage,
            archive_existing_versions=False 
        )
        print(f"Model version {model_version} transitioned to '{stage}' stage")
    except Exception as e:
        print(f"Error transitioning model stage: {e}")
    
    # Add description
    client.update_model_version(
        name=MODEL_REGISTRY_NAME,
        version=model_version,
        description=f"{model_type.upper()} model trained on {datetime.now().strftime('%Y-%m-%d')}. "
                    f"F1 Score: {best_f1_score:.4f}, Accuracy: {best_accuracy:.4f}"
    )
    
    print(f"\n{'='*60}")
    print(f"{model_type.upper()} training and registration completed!")
    print(f"{'='*60}\n")
    
    return best_params, best_run_id, model_version


def compare_models_and_promote():
    """
    Compare all models in Staging and promote the best one to Production.
    """
    client = MlflowClient()
    staging_models = client.get_latest_versions(MODEL_REGISTRY_NAME, stages=["Staging"])
    
    if len(staging_models) == 0:
        print("No models found in Staging stage")
        return None
    
    print(f"\nComparing {len(staging_models)} model(s) in Staging stage...\n")
    
    best_model = None
    best_f1_score = -1
    
    for model_version in staging_models:
        run = mlflow.get_run(model_version.run_id)
        f1_score = run.data.metrics.get('f1_score', 0)
        model_type = run.data.tags.get('model_type', 'Unknown')
        
        print(f"Model Version {model_version.version} ({model_type}):")
        print(f"  - F1 Score: {f1_score:.4f}")
        print(f"  - Run ID: {model_version.run_id}\n")
        
        if f1_score > best_f1_score:
            best_f1_score = f1_score
            best_model = model_version
    
    if best_model:
        print(f"Best model: Version {best_model.version} with F1 Score: {best_f1_score:.4f}")
        
        # Promote to Production
        client.transition_model_version_stage(
            name=MODEL_REGISTRY_NAME,
            version=best_model.version,
            stage="Production",
            archive_existing_versions=False
        )
        print(f"Model version {best_model.version} promoted to Production stage\n")
        return best_model.version
    
    return None


def list_all_model_versions():
    """
    Display all registered model versions and their stages.
    """
    client = MlflowClient()
    print(f"\n{'='*80}")
    print(f"All versions of model '{MODEL_REGISTRY_NAME}':")
    print(f"{'='*80}\n")
    
    all_versions = client.search_model_versions(f"name='{MODEL_REGISTRY_NAME}'")
    
    versions_by_stage = {"Production": [], "Staging": [], "Archived": [], "None": []}
    
    for version in all_versions:
        versions_by_stage[version.current_stage].append(version)
    
    for stage in ["Production", "Staging", "None", "Archived"]:
        if versions_by_stage[stage]:
            print(f"\n{stage} Stage:")
            print("-" * 40)
            for version in sorted(versions_by_stage[stage], key=lambda x: int(x.version)):
                try:
                    run = mlflow.get_run(version.run_id)
                    model_type = run.data.tags.get('model_type', 'Unknown')
                    f1_score = run.data.metrics.get('f1_score', 0)
                    print(f"  Version {version.version} ({model_type})")
                    print(f"    - F1 Score: {f1_score:.4f}")
                    print(f"    - Description: {version.description}")
                    print(f"    - Run ID: {version.run_id}\n")
                except Exception as e:
                    # Handle case where run data is not available locally (e.g., synced from S3)
                    print(f"  Version {version.version} (run data not available locally)")
                    print(f"    - Description: {version.description}")
                    print(f"    - Run ID: {version.run_id}")
                    print(f"    - Note: Run data not found (may be from S3 sync)\n")
    
    print(f"{'='*80}\n")


def print_registered_model_summary():
    """
    Print summary of all registered models (global registry overview).
    """
    client = MlflowClient()
    print("\n" + "="*80)
    print("Registered Models Summary (Global Overview)")
    print("="*80 + "\n")
    
    registered_models = client.search_registered_models()

    if not registered_models:
        print("No registered models found in the registry.")
    else:
        for model in registered_models:
            print(f"Model Name: {model.name}")
            for version in model.latest_versions:
                print(f"  - Version: {version.version}")
                print(f"    Stage: {version.current_stage}")
                print(f"    Run ID: {version.run_id}")
                print(f"    Description: {version.description}\n")

    print("="*80)
    print("Registry summary printed successfully.")
    print("="*80 + "\n")


# Main Execution
if __name__ == "__main__":
    
    print("\n" + "="*80)
    print("LOAN PREDICTION MODEL TRAINING - Blue-Green/Canary Deployment Setup")
    print("="*80 + "\n")
    
    # Set number of HPO trials
    MAX_EVALS = 5 
    
    # STEP 1: Train XGBoost (e.g., as the stable Production model)
    print("\n### STEP 1: Training XGBoost (Production Model) ###\n")
    xgb_params, xgb_run_id, xgb_version = train_and_register_model(
        model_type="xgboost",
        stage="Production", 
        max_evals=MAX_EVALS
    )
    
    # STEP 2: Train LightGBM (e.g., as the new Staging candidate)
    print("\n### STEP 2: Training LightGBM (Staging Model) ###\n")
    lgb_params, lgb_run_id, lgb_version = train_and_register_model(
        model_type="lightgbm",
        stage="Staging", 
        max_evals=MAX_EVALS
    )
    
    # STEP 3: Display all model versions
    list_all_model_versions()
    
    # STEP 4 (Optional): Auto-promote best Staging model
    # print("\n### STEP 4 (Optional): Comparing and Promoting Best Model ###\n")
    # promoted_version = compare_models_and_promote()
    
    # STEP 5: Global Summary
    print_registered_model_summary()

    print("\n" + "="*80)
    print("TRAINING COMPLETED!")
    print("="*80)
    print("\nNext Steps for Blue-Green/Canary Deployment:")
    print("1. Production model (XGBoost) is ready for stable traffic")
    print("2. Staging model (LightGBM) is ready for testing/canary deployment")
    print("3. Monitor metrics and promote Staging to Production if successful")
    print("="*80 + "\n")