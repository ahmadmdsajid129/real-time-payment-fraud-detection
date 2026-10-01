"""Statistical Data Drift and Model Prediction Drift Detector.

Implements Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) tests
to detect distribution shifts across features and model prediction outputs.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from scipy import stats


class DataDriftDetector:
    """Detects covariate shift and concept drift using non-parametric statistical metrics."""

    PSI_NO_DRIFT = 0.10
    PSI_CRITICAL_DRIFT = 0.25

    @staticmethod
    def calculate_psi(
        expected: np.ndarray,
        actual: np.ndarray,
        num_buckets: int = 10,
        epsilon: float = 1e-4,
    ) -> float:
        """Calculates Population Stability Index (PSI) between baseline and production arrays.
        
        PSI = sum((Actual% - Expected%) * ln(Actual% / Expected%))
        """
        expected = np.asarray(expected, dtype=float)
        actual = np.asarray(actual, dtype=float)

        # Filter NaNs or infinite values
        expected = expected[np.isfinite(expected)]
        actual = actual[np.isfinite(actual)]

        if len(expected) == 0 or len(actual) == 0:
            return 0.0

        # Define quantile bin edges based on expected reference distribution
        percentiles = np.linspace(0, 100, num_buckets + 1)
        bin_edges = np.percentile(expected, percentiles)
        bin_edges[0] = -np.inf
        bin_edges[-1] = np.inf

        # Ensure monotonic unique bins
        unique_edges = np.unique(bin_edges)
        if len(unique_edges) <= 2:
            # Constant or near-constant feature
            return 0.0

        # Bin counts
        expected_counts, _ = np.histogram(expected, bins=unique_edges)
        actual_counts, _ = np.histogram(actual, bins=unique_edges)

        # Normalize to proportions
        expected_pct = (expected_counts / len(expected)) + epsilon
        actual_pct = (actual_counts / len(actual)) + epsilon

        # Re-normalize with epsilon
        expected_pct /= np.sum(expected_pct)
        actual_pct /= np.sum(actual_pct)

        # PSI Sum
        psi_val = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        return float(max(0.0, psi_val))

    @staticmethod
    def calculate_ks_test(reference: np.ndarray, current: np.ndarray) -> Tuple[float, float]:
        """Calculates two-sample Kolmogorov-Smirnov statistic and p-value.
        
        Returns:
            (ks_statistic: float, p_value: float)
        """
        ref_clean = reference[np.isfinite(reference)]
        cur_clean = current[np.isfinite(current)]

        if len(ref_clean) == 0 or len(cur_clean) == 0:
            return 0.0, 1.0

        res = stats.ks_2samp(ref_clean, cur_clean)
        return float(res.statistic), float(res.pvalue)

    def analyze_dataset_drift(
        self,
        reference_df: pd.DataFrame,
        current_df: pd.DataFrame,
        features: List[str],
        alpha: float = 0.05,
    ) -> Dict[str, Any]:
        """Runs comprehensive drift detection across all specified features."""
        feature_reports: Dict[str, Any] = {}
        drifted_count = 0
        critical_count = 0

        for col in features:
            if col not in reference_df.columns or col not in current_df.columns:
                continue

            ref_vals = reference_df[col].values
            cur_vals = current_df[col].values

            psi = self.calculate_psi(ref_vals, cur_vals)
            ks_stat, p_val = self.calculate_ks_test(ref_vals, cur_vals)

            if psi >= self.PSI_CRITICAL_DRIFT or (p_val < alpha and ks_stat > 0.15):
                status = "CRITICAL_DRIFT"
                critical_count += 1
                drifted_count += 1
            elif psi >= self.PSI_NO_DRIFT or p_val < alpha:
                status = "MODERATE_DRIFT"
                drifted_count += 1
            else:
                status = "NO_DRIFT"

            feature_reports[col] = {
                "psi": round(psi, 4),
                "ks_statistic": round(ks_stat, 4),
                "p_value": round(p_val, 4),
                "status": status,
            }

        total_features = len(feature_reports)
        drift_rate = (drifted_count / total_features) if total_features > 0 else 0.0

        overall_status = "STABLE"
        if critical_count > 0 or drift_rate > 0.25:
            overall_status = "CRITICAL_DRIFT_DETECTED"
        elif drifted_count > 0:
            overall_status = "MODERATE_DRIFT_DETECTED"

        return {
            "overall_status": overall_status,
            "total_features_monitored": total_features,
            "drifted_features_count": drifted_count,
            "critical_features_count": critical_count,
            "feature_reports": feature_reports,
        }
