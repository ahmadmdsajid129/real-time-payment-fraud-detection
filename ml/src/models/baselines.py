"""Baseline Machine Learning Models for Fraud Classification.

Implements:
1. Dummy Classifier (Prior probability floor)
2. Logistic Regression (Interpretable linear baseline with Standard Scaler)
3. Random Forest (Nonlinear bagged decision tree ensemble baseline)
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler


class DummyBaselineModel:
    """Predicts empirical class frequency prior as the baseline performance floor."""

    def __init__(self):
        self.model = DummyClassifier(strategy="prior")
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "DummyBaselineModel":
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]


class LogisticRegressionBaseline:
    """Interpretable linear classifier with L2 regularization and zero-leakage standard scaling."""

    def __init__(self, C: float = 1.0, class_weight: str = "balanced", random_state: int = 42):
        self.scaler = StandardScaler()
        self.model = LogisticRegression(
            C=C,
            penalty="l2",
            solver="lbfgs",
            max_iter=1000,
            class_weight=class_weight,
            random_state=random_state,
        )
        self.is_fitted = False
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LogisticRegressionBaseline":
        self.feature_names = list(X.columns)
        # Scaler fitted exclusively on the training matrix
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X_scaled = self.scaler.transform(X[self.feature_names])
        return self.model.predict_proba(X_scaled)[:, 1]

    def get_coefficients(self) -> List[Tuple[str, float]]:
        """Returns sorted list of features and their linear log-odds coefficients."""
        if not self.is_fitted:
            raise ValueError("Model is not fitted.")
        coefs = self.model.coef_[0]
        feature_coefs = list(zip(self.feature_names, coefs))
        feature_coefs.sort(key=lambda x: abs(x[1]), reverse=True)
        return feature_coefs


class RandomForestBaseline:
    """Nonlinear bagged ensemble of decision trees."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 12,
        class_weight: str = "balanced",
        random_state: int = 42
    ):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            class_weight=class_weight,
            random_state=random_state,
            n_jobs=-1,
        )
        self.is_fitted = False
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RandomForestBaseline":
        self.feature_names = list(X.columns)
        self.model.fit(X[self.feature_names], y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(X[self.feature_names])[:, 1]

    def get_feature_importances(self) -> List[Tuple[str, float]]:
        """Returns features sorted by Gini impurity reduction importance."""
        if not self.is_fitted:
            raise ValueError("Model is not fitted.")
        importances = self.model.feature_importances_
        feature_imps = list(zip(self.feature_names, importances))
        feature_imps.sort(key=lambda x: x[1], reverse=True)
        return feature_imps
