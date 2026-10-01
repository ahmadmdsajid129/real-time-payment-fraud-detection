"""Unit tests for feature extraction and zero-leakage mathematical guarantees."""

from datetime import datetime, timedelta, timezone
import pytest
import pandas as pd
import numpy as np

from ml.src.features.feature_extractor import FeatureExtractor, haversine_distance
from ml.src.features.feature_definitions import FEATURE_NAMES


def test_haversine_formula():
    # Mumbai (19.0760, 72.8777) to Pune (18.5204, 73.8567) is approx 120 km
    dist = haversine_distance(19.0760, 72.8777, 18.5204, 73.8567)
    assert 110.0 <= dist <= 135.0


def test_cold_start_defaults():
    extractor = FeatureExtractor()
    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    txn = {
        "timestamp": t0,
        "amount": 2500.0,
        "lat": 19.07,
        "lon": 72.87,
        "device_id": "DEV-01",
        "country": "IN",
        "city": "Mumbai",
        "merchant_category": "GROCERY",
    }
    feats = extractor.extract_features_single(current_txn=txn)
    assert feats["txn_count_1h"] == 0
    assert feats["is_new_device"] == 1
    assert feats["amount"] == 2500.0
    assert feats["log_amount"] > 0
    assert "customer_amount_zscore" in feats


def test_zero_temporal_leakage_guarantee():
    """Verify that a current transaction amount NEVER affects its own customer_avg_amount or z-score."""
    extractor = FeatureExtractor()
    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    # Customer had two past transactions: 1000 and 2000 (mean = 1500)
    history = [
        {"timestamp": t0 - timedelta(hours=2), "amount": 1000.0, "lat": 19.0, "lon": 72.8, "country": "IN", "city": "Mumbai", "merchant_id": "M1", "device_id": "D1"},
        {"timestamp": t0 - timedelta(hours=1), "amount": 2000.0, "lat": 19.0, "lon": 72.8, "country": "IN", "city": "Mumbai", "merchant_id": "M2", "device_id": "D1"},
    ]

    # Current transaction is 50,000 (huge anomaly)
    current_txn = {
        "timestamp": t0,
        "amount": 50000.0,
        "lat": 19.0,
        "lon": 72.8,
        "device_id": "D1",
        "country": "IN",
        "city": "Mumbai",
        "merchant_category": "JEWELRY_LUXURY",
    }

    feats = extractor.extract_features_single(current_txn=current_txn, customer_history=history)

    # customer_avg_amount MUST be 1500.0 (the historical mean), NOT (1000 + 2000 + 50000) / 3 = 17666.7
    assert feats["customer_avg_amount"] == 1500.0
    # Z-score must be large and positive
    assert feats["customer_amount_zscore"] > 50.0
    # Current transaction must NOT count inside txn_count_1h before it
    # Only 1 transaction in past 1h (t0 - 1h)
    assert feats["txn_count_1h"] == 1


def test_impossible_travel_detection():
    extractor = FeatureExtractor()
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Mumbai transaction 15 minutes ago
    history = [
        {"timestamp": t0 - timedelta(minutes=15), "amount": 500.0, "lat": 19.0760, "lon": 72.8777, "country": "IN", "city": "Mumbai", "merchant_id": "M1", "device_id": "D1"},
    ]

    # Current transaction in Singapore (approx 3,900 km away) 15 minutes later
    current_txn = {
        "timestamp": t0,
        "amount": 2000.0,
        "lat": 1.3521,
        "lon": 103.8198,
        "device_id": "D1",
        "country": "SG",
        "city": "Singapore",
        "merchant_category": "ELECTRONICS",
    }

    feats = extractor.extract_features_single(current_txn=current_txn, customer_history=history)
    assert feats["impossible_travel"] == 1
    assert feats["travel_speed_kmh"] > 1000.0
    assert feats["is_new_country"] == 1


def test_batch_extraction_completeness():
    extractor = FeatureExtractor()
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    records = [
        {"transaction_id": f"TXN-{i}", "timestamp": t0 + timedelta(minutes=i*10), "customer_id": "CUST-1", "merchant_id": "M1", "amount": 100.0 * i, "country": "IN", "city": "Delhi", "lat": 28.7, "lon": 77.1, "device_id": "D1", "is_fraud": False, "merchant_category": "GROCERY"}
        for i in range(1, 10)
    ]
    df = pd.DataFrame(records)
    res = extractor.extract_features_batch(df)

    assert len(res) == 9
    for col in FEATURE_NAMES:
        assert col in res.columns
        assert not res[col].isna().any()
