"""Unit tests for Population Stability Index (PSI) and Data Drift Detection."""

import numpy as np
import pandas as pd
import pytest

from ml.src.monitoring.drift_detector import DataDriftDetector


def test_psi_identical_distributions():
    """Identical distributions must have PSI very close to 0.0."""
    np.random.seed(42)
    expected = np.random.normal(loc=100.0, scale=15.0, size=5000)
    actual = np.random.normal(loc=100.0, scale=15.0, size=5000)

    detector = DataDriftDetector()
    psi = detector.calculate_psi(expected, actual)

    assert psi < 0.05, f"Expected negligible PSI for identical samples, got {psi}"


def test_psi_extreme_drift():
    """Significant distribution shift must trigger high PSI (>= 0.25)."""
    np.random.seed(42)
    expected = np.random.normal(loc=50.0, scale=10.0, size=5000)
    # Severe shift: mean doubled and variance tripled
    actual = np.random.normal(loc=120.0, scale=30.0, size=5000)

    detector = DataDriftDetector()
    psi = detector.calculate_psi(expected, actual)

    assert psi > 0.25, f"Expected critical PSI > 0.25, got {psi}"


def test_ks_test_sensitivity():
    """Verify Kolmogorov-Smirnov test flags distinct populations."""
    np.random.seed(42)
    sample_a = np.random.exponential(scale=2.0, size=2000)
    sample_b = np.random.exponential(scale=2.0, size=2000)
    sample_c = np.random.normal(loc=5.0, scale=1.0, size=2000)

    detector = DataDriftDetector()

    # Same distribution: high p-value
    _, p_val_same = detector.calculate_ks_test(sample_a, sample_b)
    assert p_val_same > 0.05

    # Different distribution: near-zero p-value
    stat_diff, p_val_diff = detector.calculate_ks_test(sample_a, sample_c)
    assert stat_diff > 0.3
    assert p_val_diff < 1e-10


def test_dataset_drift_report():
    """Verify batch drift reporting across multiple features."""
    np.random.seed(42)
    n = 1000

    ref_df = pd.DataFrame({
        "amount": np.random.normal(100, 20, n),
        "hour_of_day": np.random.randint(0, 24, n),
        "txn_count_1h": np.random.poisson(1.5, n),
    })

    # Curated production window with amount inflation
    cur_df = pd.DataFrame({
        "amount": np.random.normal(250, 60, n),  # drifted
        "hour_of_day": np.random.randint(0, 24, n),  # stable
        "txn_count_1h": np.random.poisson(1.5, n),  # stable
    })

    detector = DataDriftDetector()
    report = detector.analyze_dataset_drift(ref_df, cur_df, features=["amount", "hour_of_day", "txn_count_1h"])

    assert report["total_features_monitored"] == 3
    assert report["feature_reports"]["amount"]["status"] in ["MODERATE_DRIFT", "CRITICAL_DRIFT"]
    assert report["feature_reports"]["hour_of_day"]["status"] == "NO_DRIFT"
