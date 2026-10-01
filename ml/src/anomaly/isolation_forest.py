"""Unsupervised Anomaly Detection using Isolation Forest.

Detects multi-dimensional structural outliers in transaction velocity,
amounts, and kinematics independently of fraud labels.
Anomaly != Fraud; anomaly score is an auxiliary risk signal.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class IsolationForestDetector:
    """Unsupervised anomaly scoring model outputting continuous scores in [0.0, 1.0]."""

    ANOMALY_FEATURE_SUBSET: List[str] = [
        "amount",
        "log_amount",
        "customer_amount_zscore",
        "amount_to_avg_ratio",
        "txn_count_1m",
        "txn_count_5m",
        "txn_count_1h",
        "travel_speed_kmh",
        "geo_distance_km",
        "time_since_prev_txn",
        "device_customer_count",
    ]

    def __init__(
        self,
        n_estimators: int = 120,
        contamination: float = 0.03,
        max_samples: float = 0.8,
        random_state: int = 42,
    ):
        self.params = {
            "n_estimators": n_estimators,
            "contamination": contamination,
            "max_samples": max_samples,
            "random_state": random_state,
            "n_jobs": -1,
        }
        self.model = IsolationForest(**self.params)
        self.is_fitted = False
        self.feature_names: List[str] = []
        # Normalization scale parameters
        self.score_min: float = -0.5
        self.score_max: float = 0.5

    def fit(self, X: pd.DataFrame) -> "IsolationForestDetector":
        """Fits Isolation Forest on historical training features."""
        # Use existing feature subset
        self.feature_names = [f for f in self.ANOMALY_FEATURE_SUBSET if f in X.columns]
        if not self.feature_names:
            self.feature_names = list(X.columns)

        X_subset = X[self.feature_names].fillna(0.0)
        self.model.fit(X_subset)

        # Establish empirical score distribution for min-max normalization
        raw_scores = self.model.decision_function(X_subset)
        self.score_min = float(np.percentile(raw_scores, 1.0))
        self.score_max = float(np.percentile(raw_scores, 99.0))
        self.is_fitted = True
        return self

    def score(self, X: pd.DataFrame) -> np.ndarray:
        """Returns continuous anomaly score in [0.0, 1.0].
        
        0.0 = completely normal inlier.
        1.0 = extreme multi-dimensional anomaly.
        """
        if not self.is_fitted:
            raise ValueError("Model is not fitted.")

        X_subset = X[self.feature_names].fillna(0.0)
        raw = self.model.decision_function(X_subset)

        # Sklearn outputs positive for inliers, negative for outliers.
        # Invert so higher value = higher anomaly.
        # Normalize: 1.0 - (raw - min) / (max - min)
        spread = max(self.score_max - self.score_min, 1e-5)
        normalized = 1.0 - ((raw - self.score_min) / spread)
        return np.clip(normalized, 0.0, 1.0)

    def score_single(self, feature_dict: Dict[str, Any]) -> float:
        """Scores a single transaction dictionary."""
        row_df = pd.DataFrame([feature_dict])
        return float(self.score(row_df)[0])
