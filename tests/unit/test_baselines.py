"""Unit tests for baseline models, temporal splitting, and metric calculations."""

from datetime import datetime, timedelta, timezone
import pytest
import numpy as np
import pandas as pd

from ml.src.data.splitter import TemporalSplitter
from ml.src.evaluation.metrics import compute_fraud_metrics
from ml.src.models.baselines import (
    DummyBaselineModel,
    LogisticRegressionBaseline,
    RandomForestBaseline,
)


@pytest.fixture
def sample_feature_df():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    records = []
    for i in range(100):
        records.append({
            "transaction_id": f"TXN-{i}",
            "timestamp": t0 + timedelta(minutes=i*15),
            "amount": 100.0 + (i * 20.0),
            "log_amount": np.log1p(100.0 + i*20.0),
            "hour_of_day": (i * 15 // 60) % 24,
            "day_of_week": (i // 96) % 7,
            "is_weekend": 0,
            "is_unusual_hour": 0,
            "txn_count_1h": i % 4,
            "customer_avg_amount": 500.0,
            "customer_std_amount": 150.0,
            "customer_amount_zscore": (100.0 + i*20.0 - 500.0) / 150.0,
            "amount_to_avg_ratio": (100.0 + i*20.0) / 501.0,
            "is_new_device": int(i % 10 == 0),
            "is_new_country": int(i % 20 == 0),
            "is_new_city": int(i % 15 == 0),
            "impossible_travel": int(i % 25 == 0),
            "geo_distance_km": 10.0 * (i % 5),
            "travel_speed_kmh": 50.0 * (i % 3),
            "merchant_risk_score": 0.2,
            "device_customer_count": 1,
            "is_fraud": int(i % 15 == 0),
        })
    return pd.DataFrame(records)


def test_temporal_splitter(sample_feature_df):
    splitter = TemporalSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    res = splitter.split(sample_feature_df)
    
    assert len(res.train_df) == 70
    assert len(res.val_df) == 15
    assert len(res.test_df) == 15
    
    # Assert strict temporal precedence
    assert res.train_df["timestamp"].max() <= res.val_df["timestamp"].min()
    assert res.val_df["timestamp"].max() <= res.test_df["timestamp"].min()


def test_metrics_calculation():
    y_true = np.array([0, 0, 0, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.8, 0.7, 0.9])
    m = compute_fraud_metrics(y_true, y_prob, threshold=0.5)

    assert m["confusion_matrix"]["true_positives"] == 2
    assert m["confusion_matrix"]["false_positives"] == 1
    assert m["confusion_matrix"]["true_negatives"] == 3
    assert m["confusion_matrix"]["false_negatives"] == 0
    assert 0.0 <= m["pr_auc"] <= 1.0
    assert 0.0 <= m["roc_auc"] <= 1.0
    assert 0.0 <= m["brier_score"] <= 1.0


def test_baseline_models_fit_and_predict(sample_feature_df):
    splitter = TemporalSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    res = splitter.split(sample_feature_df)
    
    feature_cols = [
        "amount", "log_amount", "hour_of_day", "day_of_week", "txn_count_1h",
        "customer_amount_zscore", "amount_to_avg_ratio", "is_new_device",
        "is_new_country", "impossible_travel", "merchant_risk_score"
    ]
    X_train, y_train = res.train_df[feature_cols], res.train_df["is_fraud"]
    X_test, y_test = res.test_df[feature_cols], res.test_df["is_fraud"]

    # 1. Dummy
    dummy = DummyBaselineModel()
    dummy.fit(X_train.values, y_train.values)
    dummy_p = dummy.predict_proba(X_test.values)
    assert len(dummy_p) == len(X_test)
    assert np.all((dummy_p >= 0.0) & (dummy_p <= 1.0))

    # 2. Logistic Regression
    lr = LogisticRegressionBaseline()
    lr.fit(X_train, y_train)
    lr_p = lr.predict_proba(X_test)
    assert len(lr_p) == len(X_test)
    assert np.all((lr_p >= 0.0) & (lr_p <= 1.0))
    coefs = lr.get_coefficients()
    assert len(coefs) == len(feature_cols)

    # 3. Random Forest
    rf = RandomForestBaseline(n_estimators=10, max_depth=5)
    rf.fit(X_train, y_train)
    rf_p = rf.predict_proba(X_test)
    assert len(rf_p) == len(X_test)
    assert np.all((rf_p >= 0.0) & (rf_p <= 1.0))
    imps = rf.get_feature_importances()
    assert len(imps) == len(feature_cols)
