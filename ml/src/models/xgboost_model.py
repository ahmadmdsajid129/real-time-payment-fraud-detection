"""XGBoost Primary Supervised Fraud Classifier.

Implements gradient-boosted decision trees with second-order Taylor loss optimization,
imbalance-aware gradient weighting (`scale_pos_weight`), and tree regularization.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import pandas as pd
from xgboost import XGBClassifier


class XGBoostFraudClassifier:
    """Production wrapper around XGBoost for fraud classification."""

    def __init__(
        self,
        n_estimators: int = 150,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        min_child_weight: int = 3,
        gamma: float = 0.1,
        reg_alpha: float = 0.05,
        reg_lambda: float = 1.0,
        scale_pos_weight: Optional[float] = None,
        random_state: int = 42,
    ):
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "min_child_weight": min_child_weight,
            "gamma": gamma,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "scale_pos_weight": scale_pos_weight,
            "random_state": random_state,
            "eval_metric": "logloss",
            "tree_method": "hist",
        }
        self.model = XGBClassifier(**self.params)
        self.is_fitted = False
        self.feature_names: List[str] = []

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        eval_set: Optional[List[Tuple[pd.DataFrame, pd.Series]]] = None,
        verbose: bool = False,
    ) -> "XGBoostFraudClassifier":
        self.feature_names = list(X_train.columns)

        # Automatically calculate scale_pos_weight if not specified
        if self.params["scale_pos_weight"] is None:
            n_neg = int((y_train == 0).sum())
            n_pos = int((y_train == 1).sum())
            calculated_scale = float(n_neg / max(n_pos, 1))
            self.model.set_params(scale_pos_weight=calculated_scale)
            self.params["scale_pos_weight"] = round(calculated_scale, 2)

        formatted_eval_set = None
        if eval_set:
            formatted_eval_set = [(X[self.feature_names], y) for X, y in eval_set]

        self.model.fit(
            X_train[self.feature_names],
            y_train,
            eval_set=formatted_eval_set,
            verbose=verbose,
        )
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Returns calibrated probability estimates P(y = 1 | x)."""
        if not self.is_fitted:
            raise ValueError("Model is not fitted.")
        return self.model.predict_proba(X[self.feature_names])[:, 1]

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """Returns binary predictions based on custom probability threshold."""
        probs = self.predict_proba(X)
        return (probs >= threshold).astype(int)

    def get_feature_importances(self, importance_type: str = "gain") -> List[Tuple[str, float]]:
        """Returns features sorted by importance (default: gain)."""
        if not self.is_fitted:
            raise ValueError("Model is not fitted.")
        booster = self.model.get_booster()
        score_dict = booster.get_score(importance_type=importance_type)
        
        # Map feature names
        importances = []
        for feat in self.feature_names:
            importances.append((feat, float(score_dict.get(feat, 0.0))))
        importances.sort(key=lambda x: x[1], reverse=True)
        return importances

    def get_booster(self):
        """Returns underlying XGBoost Booster object (needed for TreeSHAP)."""
        if not self.is_fitted:
            raise ValueError("Model is not fitted.")
        return self.model.get_booster()
