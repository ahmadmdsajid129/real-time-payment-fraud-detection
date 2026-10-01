"""Unit tests for synthetic transaction generator and scenario simulations."""

from datetime import datetime, timezone
import pytest
from ml.src.data.synthetic_generator import TransactionGenerator, haversine_distance
from ml.src.data.schemas import FraudScenario


def test_haversine_distance():
    # London (51.5074, -0.1278) to Paris (48.8566, 2.3522) is approx 343 km
    dist = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
    assert 330.0 < dist < 360.0


def test_generator_population_initialization():
    gen = TransactionGenerator(seed=123)
    gen.generate_population(num_customers=50, num_merchants=10)
    assert len(gen.customers) == 50
    assert len(gen.merchants) == 10
    
    # Check customer profile validity
    cust = list(gen.customers.values())[0]
    assert cust.avg_amount > 0
    assert cust.std_amount > 0
    assert len(cust.known_devices) >= 1
    assert len(cust.preferred_merchants) >= 1


def test_single_transaction_scenarios():
    gen = TransactionGenerator(seed=123)
    gen.generate_population(num_customers=20, num_merchants=5)
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Normal Scenario
    txn_normal = gen.generate_single_transaction(
        transaction_id="TXN-TEST-001",
        timestamp=t0,
        force_scenario=FraudScenario.NORMAL
    )
    assert txn_normal.is_fraud is False
    assert txn_normal.scenario == FraudScenario.NORMAL
    assert txn_normal.amount > 0

    # 2. High Value Anomaly Scenario
    txn_hva = gen.generate_single_transaction(
        transaction_id="TXN-TEST-002",
        timestamp=t0,
        force_scenario=FraudScenario.HIGH_VALUE_ANOMALY
    )
    assert txn_hva.is_fraud is True
    cust = gen.customers[txn_hva.customer_id]
    assert txn_hva.amount >= cust.avg_amount * 8.0

    # 3. New Device Scenario
    txn_dev = gen.generate_single_transaction(
        transaction_id="TXN-TEST-003",
        timestamp=t0,
        force_scenario=FraudScenario.NEW_DEVICE
    )
    assert txn_dev.is_fraud is True
    assert "UNRECOGNIZED" in txn_dev.device_id


def test_generate_stream_monotonic_order():
    gen = TransactionGenerator(seed=999)
    start_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    stream = gen.generate_stream(
        start_time=start_time,
        num_transactions=100,
        fraud_ratio=0.05
    )
    assert len(stream) == 100
    
    # Assert monotonic ordering
    for i in range(1, len(stream)):
        assert stream[i].timestamp >= stream[i - 1].timestamp

    # Check that is_fraud flag is present and roughly bounded
    fraud_count = sum(1 for t in stream if t.is_fraud)
    assert fraud_count > 0  # with 5% on 100 txns, should have positive fraud
