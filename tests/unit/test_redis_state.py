"""Unit tests for Redis Online Behavioral State Store."""

from datetime import datetime, timezone, timedelta
import pytest
from services.feature_service.redis_state import RedisStateManager


def test_idempotency_check():
    """Verify duplicate idempotency keys are detected."""
    manager = RedisStateManager()
    key = "idem-test-12345"

    assert manager.check_and_set_idempotency(key) is True
    # Second time must return False (duplicate)
    assert manager.check_and_set_idempotency(key) is False


def test_zero_leakage_history_retrieval():
    """Verify that current transaction is strictly excluded from historical lookup."""
    manager = RedisStateManager()
    cust_id = "CUST-9999"

    base_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    t1 = base_time - timedelta(minutes=10)
    t2 = base_time - timedelta(minutes=5)
    t_curr = base_time

    manager.update_state_post_decision({
        "customer_id": cust_id,
        "device_id": "DEV-01",
        "country": "US",
        "timestamp": t1,
        "amount": 50.0,
        "lat": 40.71,
        "lon": -74.00,
    })

    manager.update_state_post_decision({
        "customer_id": cust_id,
        "device_id": "DEV-01",
        "country": "US",
        "timestamp": t2,
        "amount": 75.0,
        "lat": 40.71,
        "lon": -74.00,
    })

    # Retrieve history strictly before t_curr
    history_before_curr = manager.get_customer_history(cust_id, before_timestamp_epoch=t_curr.timestamp())
    assert len(history_before_curr) == 2
    assert history_before_curr[0]["amount"] == 50.0
    assert history_before_curr[1]["amount"] == 75.0

    # Test strict zero leakage: retrieve history strictly before t2
    history_before_t2 = manager.get_customer_history(cust_id, before_timestamp_epoch=t2.timestamp())
    assert len(history_before_t2) == 1
    assert history_before_t2[0]["amount"] == 50.0


def test_known_entities_tracking():
    """Verify tracking of devices and countries."""
    manager = RedisStateManager()
    cust_id = "CUST-8888"

    assert len(manager.get_known_devices(cust_id)) == 0
    assert len(manager.get_known_countries(cust_id)) == 0

    now = datetime.now(timezone.utc)
    manager.update_state_post_decision({
        "customer_id": cust_id,
        "device_id": "DEV-A",
        "country": "US",
        "timestamp": now,
        "amount": 100.0,
        "lat": 40.71,
        "lon": -74.00,
    })

    devices = manager.get_known_devices(cust_id)
    countries = manager.get_known_countries(cust_id)

    assert "DEV-A" in devices
    assert "US" in countries

    # Add second device and country
    manager.update_state_post_decision({
        "customer_id": cust_id,
        "device_id": "DEV-B",
        "country": "CA",
        "timestamp": now + timedelta(hours=1),
        "amount": 120.0,
        "lat": 45.50,
        "lon": -73.56,
    })

    assert len(manager.get_known_devices(cust_id)) == 2
    assert "DEV-B" in manager.get_known_devices(cust_id)
    assert "CA" in manager.get_known_countries(cust_id)


def test_device_history_window():
    """Verify device history queries within 24h window."""
    manager = RedisStateManager()
    dev_id = "DEV-SYNDICATE-1"

    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    # 30 hours ago (should be excluded from 24h window)
    manager.update_state_post_decision({
        "customer_id": "CUST-1",
        "device_id": dev_id,
        "country": "US",
        "timestamp": now - timedelta(hours=30),
        "amount": 10.0,
        "lat": 40.0,
        "lon": -74.0,
    })

    # 2 hours ago (within 24h window)
    manager.update_state_post_decision({
        "customer_id": "CUST-2",
        "device_id": dev_id,
        "country": "US",
        "timestamp": now - timedelta(hours=2),
        "amount": 20.0,
        "lat": 40.0,
        "lon": -74.0,
    })

    history = manager.get_device_history(dev_id, before_timestamp_epoch=now.timestamp())
    assert len(history) == 1
    assert history[0]["customer_id"] == "CUST-2"
