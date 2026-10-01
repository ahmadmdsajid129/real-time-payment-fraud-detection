"""Probability Calibration Engine for Tree-Based Classifiers.

Transforms raw uncalibrated decision margins or probabilities into reliable
empirical fraud probabilities using Isotonic Regression or Platt Scaling.
Strict Rule: Calibrators MUST be fitted on the validation split, never on test data.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss


class ProbabilityCalibrator:
    """Calibrates 1D probability predictions using Isotonic Regression or Platt Sigmoid."""

    def __init__(self, method: str = "isotonic"):
        if method not in ["isotonic", "sigmoid"]:
            raise ValueError("Method must be 'isotonic' or 'sigmoid'")
        self.method = method
        self.is_fitted = False
        if method == "isotonic":
            self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        else:
            self.calibrator = LogisticRegression(C=1.0, solver="lbfgs")

    def fit(self, raw_probs: np.ndarray, y_val: np.ndarray) -> "ProbabilityCalibrator":
        raw_probs = np.asarray(raw_probs, dtype=float)
        y_val = np.asarray(y_val, dtype=int)

        if self.method == "isotonic":
            self.calibrator.fit(raw_probs, y_val)
        else:
            # Platt scaling operates in 2D array for Logistic Regression
            self.calibrator.fit(raw_probs.reshape(-1, 1), y_val)

        self.is_fitted = True
        return self

    def predict_proba(self, raw_probs: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise ValueError("Calibrator is not fitted.")
        raw_probs = np.asarray(raw_probs, dtype=float)

        if self.method == "isotonic":
            calibrated = self.calibrator.predict(raw_probs)
        else:
            calibrated = self.calibrator.predict_proba(raw_probs.reshape(-1, 1))[:, 1]

        # Enforce strict probability bounds [0.0, 1.0]
        return np.clip(calibrated, 0.0, 1.0)

    @staticmethod
    def compute_calibration_curve(
        y_true: np.ndarray,
        y_prob: np.ndarray,
        n_bins: int = 10,
    ) -> Dict[str, Any]:
        """Computes empirical reliability diagram coordinates and Expected Calibration Error (ECE)."""
        y_true = np.asarray(y_true, dtype=int)
        y_prob = np.asarray(y_prob, dtype=float)

        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        bin_centers = []
        true_fractions = []
        bin_counts = []
        ece = 0.0
        n_total = len(y_true)

        for i in range(n_bins):
            start = bin_edges[i]
            end = bin_edges[i + 1]
            if i == n_bins - 1:
                mask = (y_prob >= start) & (y_prob <= end)
            else:
                mask = (y_prob >= start) & (y_prob < end)

            count = int(np.sum(mask))
            bin_counts.append(count)
            center = (start + end) / 2.0
            bin_centers.append(round(center, 3))

            if count > 0:
                actual_frac = float(np.mean(y_true[mask]))
                mean_pred = float(np.mean(y_prob[mask]))
                true_fractions.append(round(actual_frac, 4))
                ece += (count / n_total) * abs(actual_frac - mean_pred)
            else:
                true_fractions.append(0.0)

        brier = float(brier_score_loss(y_true, y_prob))

        return {
            "brier_score": round(brier, 4),
            "expected_calibration_error": round(float(ece), 4),
            "bin_centers": bin_centers,
            "true_fractions": true_fractions,
            "bin_counts": bin_counts,
        }
