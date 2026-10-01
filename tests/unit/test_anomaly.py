"""Unit tests for unsupervised anomaly detection and behavioral profiling."""

import pytest
import numpy as np
import pandas as pd
from ml.src.anomaly.isolation_forest import IsolationForestDetector
from ml.src.features.behavioral_profiler import BehavioralProfiler


@pytest.fixture
def sample_feature_data():
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        "amount": np.random.exponential(scale=1000, size=n),
        "log_amount": np.log1p(np.random.exponential(scale=1000, size=n)),
        "customer_amount_zscore": np.random.normal(loc=0, scale=1, size=n),
        "amount_to_avg_ratio": np.random.uniform(0.5, 2.0, size=n),
        "txn_count_1m": np.random.poisson(lam=0.2, size=n),
        "txn_count_5m": np.random.poisson(lam=0.5, size=n),
        "txn_count_1h": np.random.poisson(lam=1.5, size=n),
        "travel_speed_kmh": np.random.uniform(0, 100, size=n),
        "geo_distance_km": np.random.uniform(0, 50, size=n),
        "time_since_prev_txn": np.random.exponential(scale=3600, size=n),
        "device_customer_count": np.ones(n),
    })
    return df


def test_isolation_forest_scoring_bounds(sample_feature_data):
    detector = IsolationForestDetector(n_estimators=30)
    detector.fit(sample_feature_data)

    scores = detector.score(sample_feature_data)
    assert len(scores) == len(sample_feature_data)
    assert np.all((scores >= 0.0) & (scores <= 1.0))

    # Test that extreme outlier scores higher than median inlier
    outlier_row = pd.DataFrame([{
        "amount": 250000.0,
        "log_amount": 12.4,
        "customer_amount_zscore": 25.0,
        "amount_to_avg_ratio": 50.0,
        "txn_count_1m": 8,
        "txn_count_5m": 15,
        "txn_count_1h": 30,
        "travel_speed_kmh": 2500.0,
        "geo_distance_km": 5000.0,
        "time_since_prev_txn": 2.0,
        "device_customer_count": 8,
    }])
    outlier_score = detector.score(outlier_row)[0]
    median_inlier_score = float(np.median(scores))
    assert outlier_score > median_inlier_score


def test_behavioral_profiler_normal_vs_anomalous():
    # 1. Normal customer behavior
    normal_features = {
        "customer_amount_zscore": 0.4,
        "amount_to_avg_ratio": 1.1,
        "txn_count_1m": 0,
        "txn_count_1h": 1,
        "travel_speed_kmh": 25.0,
        "impossible_travel": 0,
        "is_new_device": 0,
        "is_new_country": 0,
        "is_new_city": 0,
        "is_unusual_hour": 0,
    }
    score_norm, signals_norm = BehavioralProfiler.score_behavior(normal_features)
    assert 0.0 <= score_norm <= 0.2
    assert len(signals_norm) == 0

    # 2. Extreme anomalous behavior
    attack_features = {
        "customer_amount_zscore": 8.5,
        "amount_to_avg_ratio": 15.0,
        "txn_count_1m": 4,
        "txn_count_1h": 8,
        "travel_speed_kmh": 1500.0,
        "impossible_travel": 1,
        "is_new_device": 1,
        "is_new_country": 1,
        "is_new_city": 1,
        "is_unusual_hour": 1,
    }
    score_attack, signals_attack = BehavioralProfiler.score_behavior(attack_features)
    assert score_attack > 0.85
    assert "AMOUNT_HIGH_ZSCORE" in signals_attack
    assert "IMPOSSIBLE_TRAVEL_SPEED" in signals_attack
    assert "NEW_DEVICE_DETECTED" in signals_attack
