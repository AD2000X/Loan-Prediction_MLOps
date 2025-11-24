from sklearn.base import BaseEstimator, TransformerMixin
from prediction_model.config import config
import numpy as np


class MeanImputer(BaseEstimator, TransformerMixin):
    """
    Custom transformer to impute missing values with the mean of the column.
    """
    def __init__(self, variables=None):
        """
        Initializes the imputer.
        :param variables: List of numerical features to impute.
        """
        self.variables = variables
        self._transform_output = None

    def fit(self, X, y=None):
        """
        Learns the mean for each specified variable from the training data.
        :param X: Training data (pandas DataFrame).
        :return: self
        """
        self.mean_dict = {col: X[col].mean() for col in self.variables}
        return self

    def transform(self, X):
        """
        Applies the learned mean imputation to the input data.
        :param X: Data to transform (pandas DataFrame).
        :return: Transformed data (pandas DataFrame or numpy array).
        """
        X = X.copy()
        for col in self.variables:
            X[col].fillna(self.mean_dict[col], inplace=True)
        if self._transform_output == "numpy":
            return X.to_numpy()
        return X

    def set_output(self, *, transform=None):
        """
        (scikit-learn compatible) Sets the output format of the transform method.
        """
        self._transform_output = transform
        return self


class ModeImputer(BaseEstimator, TransformerMixin):
    """
    Custom transformer to impute missing values with the mode (most frequent value) 
    of the column, typically used for categorical features.
    """
    def __init__(self, variables=None):
        """
        Initializes the imputer.
        :param variables: List of categorical features to impute.
        """
        self.variables = variables
        self._transform_output = None

    def fit(self, X, y=None):
        """
        Learns the mode for each specified variable from the training data.
        Handles edge cases where columns may be all NaN.
        :param X: Training data (pandas DataFrame).
        :return: self
        """
        # Calculate the mode (most frequent value) for each variable
        self.mode_dict = {}
        for col in self.variables:
            mode_values = X[col].mode(dropna=True)
            # Handle case where column is all NaN (mode returns empty Series)
            if len(mode_values) > 0:
                self.mode_dict[col] = mode_values[0]
            else:
                # Use None as fallback for all-NaN columns
                # In transform, these will remain NaN
                self.mode_dict[col] = None
        return self

    def transform(self, X):
        """
        Applies the learned mode imputation to the input data.
        :param X: Data to transform (pandas DataFrame).
        :return: Transformed data (pandas DataFrame or numpy array).
        """
        X = X.copy()
        for col in self.variables:
            # Only fill if mode_dict has a valid value (not None)
            if self.mode_dict[col] is not None:
                X[col].fillna(self.mode_dict[col], inplace=True)
        if self._transform_output == "numpy":
            return X.to_numpy()
        return X

    def set_output(self, *, transform=None):
        """
        (scikit-learn compatible) Sets the output format of the transform method.
        """
        self._transform_output = transform
        return self


class DropColumns(BaseEstimator, TransformerMixin):
    """
    Custom transformer to drop specified columns from the DataFrame.
    """
    def __init__(self, variables_to_drop=None):
        """
        Initializes the dropper.
        :param variables_to_drop: List of features to drop.
        """
        self.variables_to_drop = variables_to_drop
        self._transform_output = None

    def fit(self, X, y=None):
        """
        No operation needed for fitting as column names are known beforehand.
        :return: self
        """
        return self

    def transform(self, X):
        """
        Drops the specified columns from the input data.
        :param X: Data to transform (pandas DataFrame).
        :return: Transformed data (pandas DataFrame or numpy array).
        """
        X = X.copy()
        X = X.drop(columns=self.variables_to_drop)
        if self._transform_output == "numpy":
            return X.to_numpy()
        return X

    def set_output(self, *, transform=None):
        """
        (scikit-learn compatible) Sets the output format of the transform method.
        """
        self._transform_output = transform
        return self


class DomainProcessing(BaseEstimator, TransformerMixin):
    """
    Custom transformer for domain-specific feature engineering.
    In this case, it adds one variable's value to another (e.g., Applicant Income + Coapplicant Income).
    """
    def __init__(self, variable_to_modify=None, variable_to_add=None):
        """
        Initializes the processor.
        :param variable_to_modify: List of features whose values will be increased.
        :param variable_to_add: The feature whose value will be added to the others.
        """
        self.variable_to_modify = variable_to_modify
        self.variable_to_add = variable_to_add
        self._transform_output = None

    def fit(self, X, y=None):
        """
        No operation needed for fitting.
        :return: self
        """
        return self

    def transform(self, X):
        """
        Performs the domain processing (feature addition).
        :param X: Data to transform (pandas DataFrame).
        :return: Transformed data (pandas DataFrame or numpy array).
        """
        X = X.copy()
        for feature in self.variable_to_modify:
            X[feature] = X[feature] + X[self.variable_to_add]
        if self._transform_output == "numpy":
            return X.to_numpy()
        return X

    def set_output(self, *, transform=None):
        """
        (scikit-learn compatible) Sets the output format of the transform method.
        """
        self._transform_output = transform
        return self


class CustomLabelEncoder(BaseEstimator, TransformerMixin):
    """
    Custom ordinal encoder that assigns integer labels based on the frequency 
    (or count) of each category, sorting them from least frequent (0) to most frequent (max).
    """
    def __init__(self, variables=None):
        """
        Initializes the encoder.
        :param variables: List of categorical features to encode.
        """
        self.variables = variables
        self._transform_output = None

    def fit(self, X, y=None):
        """
        Learns the label-to-integer mapping based on category frequency in the training data.
        :param X: Training data (pandas DataFrame).
        :return: self
        """
        self.label_dict = {}
        for var in self.variables:
            t = X[var].value_counts().sort_values(ascending=True).index
            self.label_dict[var] = {k: i for i, k in enumerate(t, 0)}
        return self

    def transform(self, X):
        """
        Applies the learned label encoding to the input data.
        :param X: Data to transform (pandas DataFrame).
        :return: Transformed data (pandas DataFrame or numpy array).
        """
        X = X.copy()
        for feature in self.variables:
            X[feature] = X[feature].map(self.label_dict[feature])
        if self._transform_output == "numpy":
            return X.to_numpy()
        return X

    def set_output(self, *, transform=None):
        """
        (scikit-learn compatible) Sets the output format of the transform method.
        """
        self._transform_output = transform
        return self


class LogTransforms(BaseEstimator, TransformerMixin):
    """
    Custom transformer to apply a natural logarithm transformation (log(x)) 
    to specified numerical features, often used to normalize skewed distributions.
    """
    def __init__(self, variables=None):
        """
        Initializes the transformer.
        :param variables: List of numerical features to log transform.
        """
        self.variables = variables
        self._transform_output = None

    def fit(self, X, y=None):
        """
        No operation needed for fitting.
        :return: self
        """
        return self

    def transform(self, X):
        """
        Applies the natural logarithm transformation to the input data.
        Uses log1p(x) = log(1+x) to handle zero values safely.
        :param X: Data to transform (pandas DataFrame).
        :return: Transformed data (pandas DataFrame or numpy array).
        """
        X = X.copy()
        for col in self.variables:
            # Use log1p to safely handle zero values
            # This computes log(1 + x), so log1p(0) = 0
            X[col] = np.log1p(X[col])
        if self._transform_output == "numpy":
            return X.to_numpy()
        return X

    def set_output(self, *, transform=None):
        """
        (scikit-learn compatible) Sets the output format of the transform method.
        """
        self._transform_output = transform
        return self