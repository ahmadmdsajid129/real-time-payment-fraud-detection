"""Unit tests for probability calibration and threshold optimization."""

import pytest
import numpy as np
import pandas as pd
from ml.src.calibration.calibrator import ProbabilityCalibrator
from ml.src.evaluation.cost_optimization import ThresholdOptimizer


@pytest.fixture
def synthetic_val_probs():
    np.random.seed(42)
    n = 200
    # True binary outcomes
    y = np.random.binomial(n=1, p=0.1, size=n)
    # Distorted raw probabilities (e.g. overconfident)
    raw = np.where(y == 1, np.random.beta(5, 2, size=n), np.random.beta(1, 5, size=n))
    return raw, y


def test_isotonic_calibrator_bounds_and_monotonicity(synthetic_val_probs):
    raw, y = synthetic_val_probs
    calibrator = ProbabilityCalibrator(method="isotonic")
    calibrator.fit(raw, y)

    test_inputs = np.linspace(0.0, 1.0, 50)
    calibrated = calibrator.predict_proba(test_inputs)

    assert len(calibrated) == len(test_inputs)
    assert np.all((calibrated >= 0.0) & (calibrated <= 1.0))
    # Test monotonic non-decreasing property of isotonic regression
    for i in range(1, len(calibrated)):
        assert calibrated[i] >= calibrated[i - 1] - 1e-7


def test_platt_sigmoid_calibrator(synthetic_val_probs):
    raw, y = synthetic_val_probs
    calibrator = ProbabilityCalibrator(method="sigmoid")
    calibrator.fit(raw, y)

    test_inputs = np.linspace(0.0, 1.0, 20)
    calibrated = calibrator.predict_proba(test_inputs)
    assert len(calibrated) == len(test_inputs)
    assert np.all((calibrated >= 0.0) & (calibrated <= 1.0))


def test_calibration_curve_metrics(synthetic_val_probs):
    raw, y = synthetic_val_probs
    curve = ProbabilityCalibrator.compute_calibration_curve(y, raw, n_bins=10)

    assert "brier_score" in curve
    assert "expected_calibration_error" in curve
    assert curve["brier_score"] >= 0.0
    assert curve["expected_calibration_error"] >= 0.0
    assert len(curve["bin_centers"]) == 10
    assert len(curve["true_fractions"]) == 10


def test_threshold_optimizer():
    np.random.seed(42)
    n = 100
    y_true = np.array([0]*90 + [1]*10)
    y_prob = np.linspace(0.05, 0.95, n)

    optimizer = ThresholdOptimizer(
        cost_chargeback_penalty=25.0,
        cost_customer_insult=35.0,
        cost_analyst_review=4.0
    )
    res = optimizer.find_optimal_thresholds(y_true, y_prob)

    assert 0.0 < res["optimal_f2_threshold"] < 1.0
    assert 0.0 < res["optimal_cost_threshold"] < 1.0
    assert "precision" in res["optimal_f2_metrics"]
    assert "total_cost" in res["optimal_cost_metrics"]
