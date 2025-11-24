"""Expose preprocessing pipeline at package root for backward compatibility."""

from prediction_model.processing.pipeline import preprocessing_pipeline

__all__ = ["preprocessing_pipeline"]
