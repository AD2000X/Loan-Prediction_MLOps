"""
Improved prediction module with MLflow Model Registry integration
Supports loading models by stage (Production/Staging) or by version number
Enables Blue-Green and Canary deployment strategies
"""

import os
import re
import mlflow
from mlflow.tracking import MlflowClient

# Then build loader class / client
client = MlflowClient()

DEBUG = False

if DEBUG:
    print("Tracking URI:", mlflow.get_tracking_uri())
    try:
        all_models = client.search_model_versions("name LIKE '%'")
        model_names = sorted(list({m.name for m in all_models}))
        print("Registered Models:", model_names)
    except Exception as e:
        print(f"Unable to list registered models: {e}")

import pandas as pd
import numpy as np
from prediction_model.config import config
from typing import Union, Dict, List


def _load_model_with_path_fallback(model_uri: str):
    """
    Load model with automatic path resolution fallback.

    Handles cases where Model Registry contains GitHub Actions absolute paths
    by converting them to relative paths in the current environment.

    Args:
        model_uri: MLflow model URI (e.g., "models:/LoanPrediction/Production")

    Returns:
        Loaded model

    Raises:
        Exception: If model cannot be loaded even after path resolution
    """
    try:
        # Try loading model directly
        return mlflow.sklearn.load_model(model_uri)
    except (FileNotFoundError, OSError) as e:
        print(f"Direct model load failed: {e}")
        print("Attempting to resolve model path...")

        # Extract model name and stage/version from URI
        # URI formats: "models:/LoanPrediction/Production" or "models:/LoanPrediction/5"
        match = re.match(r"models:/([^/]+)/(.+)", model_uri)
        if not match:
            raise ValueError(f"Invalid model URI format: {model_uri}")

        model_name, stage_or_version = match.groups()

        # Get model version info from registry
        try:
            # Check if stage_or_version is a number (version) or stage name
            if stage_or_version.isdigit():
                model_version = client.get_model_version(model_name, stage_or_version)
            else:
                # Get latest version for the stage
                versions = client.get_latest_versions(model_name, stages=[stage_or_version])
                if not versions:
                    raise Exception(f"No model found for stage '{stage_or_version}'")
                model_version = versions[0]

            # Get the model source path from registry
            source_path = model_version.source
            print(f"Registry source path: {source_path}")

            # Check if path is absolute GitHub Actions path
            if "/home/runner/work/" in source_path or "C:/" in source_path or source_path.startswith("/"):
                print("Detected absolute path, converting to relative...")

                # Extract the relative path from mlruns directory onwards
                # Pattern: .../.../mlruns/EXPERIMENT_ID/RUN_ID/artifacts/MODEL_NAME
                mlruns_match = re.search(r'(mlruns/.+)', source_path)
                if mlruns_match:
                    relative_path = mlruns_match.group(1)
                    # Remove trailing '/.' if present
                    relative_path = relative_path.rstrip('/.')

                    print(f"Resolved relative path: {relative_path}")

                    # Try loading from relative path
                    if os.path.exists(relative_path):
                        return mlflow.sklearn.load_model(f"file://{os.path.abspath(relative_path)}")
                    else:
                        print(f"Warning: Resolved path does not exist: {relative_path}")
                        raise FileNotFoundError(f"Model not found at {relative_path}")
                else:
                    print("Could not extract mlruns path from source")
                    raise
            else:
                # Path is already relative, this shouldn't happen if direct load failed
                raise

        except Exception as inner_e:
            print(f"Path resolution failed: {inner_e}")
            raise Exception(f"Failed to load model from {model_uri}: {e}") from inner_e


class ModelLoader:
    """
    Load models from MLflow Model Registry by stage or version
    
    This class provides flexible model loading to support:
    - Blue-Green deployment (switch between Production/Staging)
    - Canary deployment (gradual traffic shift)
    - Version-specific loading for testing
    """
    
    def __init__(self, model_name: str = "LoanPrediction"):
        """
        Initialize ModelLoader
        
        Args:
            model_name: Name of the model in MLflow Model Registry
        """
        self.client = client
        self.model_name = model_name
        self.cache = {}  # Cache loaded models to improve performance
        
    def load_model_by_stage(self, stage: str = "Production"):
        """
        Load model from specific stage (Production or Staging)

        This method is used in production to dynamically load models
        based on their deployment stage.

        Args:
            stage: MLflow Model Registry stage ("Production" or "Staging")

        Returns:
            Loaded scikit-learn pipeline (preprocessing + model)

        Example:
            loader = ModelLoader()
            model = loader.load_model_by_stage("Production")  # Load production model
            model = loader.load_model_by_stage("Staging")     # Load canary model
        """
        cache_key = f"stage_{stage}"

        # Check cache first (avoid reloading same model)
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            model_uri = f"models:/{self.model_name}/{stage}"
            model = _load_model_with_path_fallback(model_uri)
            self.cache[cache_key] = model
            return model
        except Exception as e:
            print(f"Error loading model from stage '{stage}': {e}")
            raise
    
    def load_model_by_version(self, version: Union[int, str]):
        """
        Load specific model version by version number

        Useful for:
        - Testing specific model versions
        - Rollback to previous versions
        - A/B testing with specific versions

        Args:
            version: Version number (e.g., 1, 2, 3, or "1", "2", "3")

        Returns:
            Loaded scikit-learn pipeline

        Example:
            loader = ModelLoader()
            model = loader.load_model_by_version(1)  # Load version 1
            model = loader.load_model_by_version(2)  # Load version 2
        """
        cache_key = f"version_{version}"

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            model_uri = f"models:/{self.model_name}/{version}"
            model = _load_model_with_path_fallback(model_uri)
            self.cache[cache_key] = model
            return model
        except Exception as e:
            print(f"Error loading model version '{version}': {e}")
            raise
    
    def get_model_info(self, stage: str = "Production") -> Dict:
        """
        Get metadata about the model in specified stage
        
        Useful for logging, monitoring, and displaying model information
        
        Args:
            stage: "Production" or "Staging"
        
        Returns:
            Dictionary containing:
            - version: Model version number
            - stage: Current stage
            - model_type: "XGBoost" or "LightGBM"
            - f1_score: F1 score from training
            - accuracy: Accuracy from training
            - run_id: MLflow run ID
        
        Example:
            loader = ModelLoader()
            info = loader.get_model_info("Production")
            print(f"Using {info['model_type']} v{info['version']}")
        """
        try:
            versions = self.client.get_latest_versions(self.model_name, stages=[stage])
            
            if not versions:
                return {
                    "error": f"No model found in stage '{stage}'",
                    "version": None,
                    "stage": stage
                }
            
            version = versions[0]
            run = mlflow.get_run(version.run_id)
            
            return {
                "version": version.version,
                "stage": stage,
                "model_type": run.data.tags.get("model_type", "Unknown"),
                "f1_score": run.data.metrics.get("f1_score", 0),
                "accuracy": run.data.metrics.get("accuracy", 0),
                "recall": run.data.metrics.get("recall", 0),
                "precision": run.data.metrics.get("precision", 0),
                "run_id": version.run_id,
                "description": version.description
            }
        except Exception as e:
            return {
                "error": str(e),
                "version": None,
                "stage": stage
            }
    
    def get_version_info(self, version: Union[int, str]) -> Dict:
        """
        Get metadata about a specific model version
        
        Args:
            version: Version number
        
        Returns:
            Dictionary with model information
        """
        try:
            model_version = self.client.get_model_version(
                name=self.model_name,
                version=str(version)
            )
            run = mlflow.get_run(model_version.run_id)
            
            return {
                "version": model_version.version,
                "stage": model_version.current_stage,
                "model_type": run.data.tags.get("model_type", "Unknown"),
                "f1_score": run.data.metrics.get("f1_score", 0),
                "accuracy": run.data.metrics.get("accuracy", 0),
                "run_id": model_version.run_id,
                "description": model_version.description
            }
        except Exception as e:
            return {
                "error": str(e),
                "version": version
            }
    
    def list_all_versions(self) -> List[Dict]:
        """
        List all available model versions
        
        Returns:
            List of dictionaries with version information
        """
        try:
            all_versions = self.client.search_model_versions(f"name='{self.model_name}'")
            
            result = []
            for version in all_versions:
                run = mlflow.get_run(version.run_id)
                result.append({
                    "version": version.version,
                    "stage": version.current_stage,
                    "model_type": run.data.tags.get("model_type", "Unknown"),
                    "f1_score": run.data.metrics.get("f1_score", 0),
                    "run_id": version.run_id
                })
            
            return sorted(result, key=lambda x: int(x["version"]), reverse=True)
        except Exception as e:
            print(f"Error listing versions: {e}")
            return []


def generate_predictions(
    data_input: Union[List[Dict], pd.DataFrame],
    stage: str = None,
    version: Union[int, str] = None
) -> Dict:
    """
    Generate predictions using model from specified stage or version
    
    This function supports multiple deployment scenarios:
    1. Production traffic: stage="Production"
    2. Canary traffic: stage="Staging"
    3. Testing specific version: version=1
    
    Args:
        data_input: Input data (list of dicts or DataFrame)
        stage: "Production" or "Staging" (if None, uses environment variable or defaults to "Production")
        version: Specific version number (overrides stage if provided)
    
    Returns:
        Dictionary containing:
        - prediction: Array of predictions ('Y' or 'N')
        - model_version: Version number used
        - model_type: Model type ("XGBoost" or "LightGBM")
        - model_stage: Stage used ("Production" or "Staging")
    
    Example:
        # Use production model
        result = generate_predictions(data, stage="Production")
        
        # Use staging model (canary)
        result = generate_predictions(data, stage="Staging")
        
        # Use specific version
        result = generate_predictions(data, version=2)
    """
    # Convert input to DataFrame if needed
    data = pd.DataFrame(data_input)
    
    # Initialize model loader
    loader = ModelLoader()
    
    # Determine which model to load
    if version is not None:
        # Load specific version
        model = loader.load_model_by_version(version)
        model_info = loader.get_version_info(version)
        print(f"[PREDICTION] Using {model_info['model_type']} model version {version} (stage: {model_info['stage']})")
    else:
        # Load by stage (default to Production if not specified)
        if stage is None:
            stage = os.getenv("MODEL_STAGE", "Production")
        
        model = loader.load_model_by_stage(stage)
        model_info = loader.get_model_info(stage)
        
        if "error" in model_info:
            raise ValueError(f"Failed to load model: {model_info['error']}")
        
        print(f"[PREDICTION] Using {model_info['model_type']} model v{model_info['version']} from {stage} stage")
        print(f"[PREDICTION] Model metrics - F1: {model_info['f1_score']:.4f}, Accuracy: {model_info['accuracy']:.4f}")
    
    # Make predictions
    try:
        prediction = model.predict(data)
        output = np.where(prediction == 1, 'Y', 'N')
        
        result = {
            "prediction": output,
            "model_version": model_info['version'],
            "model_type": model_info.get('model_type', 'Unknown'),
            "model_stage": model_info.get('stage', 'Unknown')
        }
        
        return result
    
    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        raise


def generate_predictions_batch(
    data_input: pd.DataFrame,
    stage: str = None,
    version: Union[int, str] = None
) -> Dict:
    """
    Generate batch predictions using model from specified stage or version
    
    Similar to generate_predictions but optimized for batch processing
    
    Args:
        data_input: DataFrame with features
        stage: "Production" or "Staging" (defaults to environment variable or "Production")
        version: Specific version number (overrides stage if provided)
    
    Returns:
        Dictionary containing:
        - prediction: Array of predictions
        - model_version: Version number used
        - model_type: Model type
        - model_stage: Stage used
    
    Example:
        df = pd.read_csv("batch_data.csv")
        result = generate_predictions_batch(df, stage="Production")
    """
    # Initialize model loader
    loader = ModelLoader()
    
    # Determine which model to load
    if version is not None:
        model = loader.load_model_by_version(version)
        model_info = loader.get_version_info(version)
        print(f"[BATCH] Using {model_info['model_type']} model version {version}")
    else:
        if stage is None:
            stage = os.getenv("MODEL_STAGE", "Production")
        
        model = loader.load_model_by_stage(stage)
        model_info = loader.get_model_info(stage)
        
        if "error" in model_info:
            raise ValueError(f"Failed to load model: {model_info['error']}")
        
        print(f"[BATCH] Using {model_info['model_type']} model v{model_info['version']} from {stage} stage")
    
    # Make predictions
    try:
        prediction = model.predict(data_input)
        output = np.where(prediction == 1, 'Y', 'N')
        
        result = {
            "prediction": output,
            "model_version": model_info['version'],
            "model_type": model_info.get('model_type', 'Unknown'),
            "model_stage": model_info.get('stage', 'Unknown')
        }
        
        return result
    
    except Exception as e:
        print(f"[ERROR] Batch prediction failed: {e}")
        raise


def compare_predictions(data_input: Union[List[Dict], pd.DataFrame]) -> Dict:
    """
    Compare predictions from Production and Staging models
    
    Useful for:
    - Validating new models before full rollout
    - A/B testing analysis
    - Understanding prediction differences
    
    Args:
        data_input: Input data (list of dicts or DataFrame)
    
    Returns:
        Dictionary containing:
        - production_predictions: Predictions from Production model
        - staging_predictions: Predictions from Staging model
        - agreement_rate: Percentage of predictions that match
        - production_info: Production model metadata
        - staging_info: Staging model metadata
    
    Example:
        comparison = compare_predictions(test_data)
        print(f"Agreement rate: {comparison['agreement_rate']:.2%}")
    """
    # Get predictions from both models
    prod_result = generate_predictions(data_input, stage="Production")
    staging_result = generate_predictions(data_input, stage="Staging")
    
    # Calculate agreement
    prod_pred = prod_result['prediction']
    staging_pred = staging_result['prediction']
    agreement = np.mean(prod_pred == staging_pred)
    
    return {
        "production_predictions": prod_pred,
        "staging_predictions": staging_pred,
        "agreement_rate": agreement,
        "production_info": {
            "version": prod_result['model_version'],
            "type": prod_result['model_type']
        },
        "staging_info": {
            "version": staging_result['model_version'],
            "type": staging_result['model_type']
        }
    }


# Backward compatibility with original predict.py
# This ensures existing code using the old function signature still works
if __name__ == '__main__':
    # Example usage
    print("\n=== Model Loader Demo ===\n")
    
    loader = ModelLoader()
    
    # List all available models
    print("Available model versions:")
    versions = loader.list_all_versions()
    for v in versions:
        print(f"  v{v['version']} - {v['model_type']} ({v['stage']}) - F1: {v['f1_score']:.4f}")
    
    # Get production model info
    print("\nProduction model info:")
    prod_info = loader.get_model_info("Production")
    print(f"  Version: {prod_info['version']}")
    print(f"  Type: {prod_info['model_type']}")
    print(f"  F1 Score: {prod_info['f1_score']:.4f}")
    
    # Get staging model info
    print("\nStaging model info:")
    staging_info = loader.get_model_info("Staging")
    print(f"  Version: {staging_info['version']}")
    print(f"  Type: {staging_info['model_type']}")
    print(f"  F1 Score: {staging_info['f1_score']:.4f}")