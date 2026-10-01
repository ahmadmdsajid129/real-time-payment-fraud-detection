"""Unit tests for ColdStartManager and EntityResolver."""

import pytest
from services.risk_engine.entity_resolution import (
    ColdStartManager,
    EntityResolver,
    AccountMaturity,
)


def test_account_maturity_lifecycle():
    manager = ColdStartManager()

    assert manager.determine_maturity(0) == AccountMaturity.COLD_START
    assert manager.determine_maturity(1) == AccountMaturity.WARMING
    assert manager.determine_maturity(3) == AccountMaturity.WARMING
    assert manager.determine_maturity(4) == AccountMaturity.MATURE
    assert manager.determine_maturity(100) == AccountMaturity.MATURE


def test_bayesian_shrinkage_cold_start():
    """Empty history must return population defaults."""
    manager = ColdStartManager(population_avg_amount=100.0, population_std_amount=30.0, prior_weight_m=5.0)

    mu, std = manager.compute_bayesian_shrunk_baseline([])
    assert mu == 100.0
    assert std == 30.0


def test_bayesian_shrinkage_single_transaction():
    """Single extreme transaction must be shrunk toward the population mean."""
    manager = ColdStartManager(population_avg_amount=100.0, population_std_amount=30.0, prior_weight_m=5.0)

    # 1 transaction of $700 (7x population average)
    # Expected: (1 * 700 + 5 * 100) / (1 + 5) = 1200 / 6 = 200.0
    mu, std = manager.compute_bayesian_shrunk_baseline([700.0])
    assert mu == 200.0
    assert std == 30.0


def test_bayesian_shrinkage_mature_convergence():
    """Large N must converge toward empirical sample average."""
    manager = ColdStartManager(population_avg_amount=100.0, population_std_amount=30.0, prior_weight_m=5.0)

    # 50 transactions averaging $500
    amounts = [500.0] * 50
    # Expected: (50 * 500 + 5 * 100) / 55 = 25500 / 55 = 463.64
    mu, std = manager.compute_bayesian_shrunk_baseline(amounts)
    assert 460.0 < mu < 465.0


def test_device_syndicate_detection():
    resolver = EntityResolver(syndicate_threshold_custs=3)
    dev_id = "DEV-SHARED-CARDING-01"

    # 1. Device used by only 1 cardholder
    past_txns_single = [{"customer_id": "CUST-A"}]
    is_syn, count, boost = resolver.evaluate_device_syndicate(dev_id, "CUST-A", past_txns_single)
    assert is_syn is False
    assert count == 1
    assert boost == 0.0

    # 2. Device used by 4 distinct cardholders within 24h
    past_txns_multi = [
        {"customer_id": "CUST-A"},
        {"customer_id": "CUST-B"},
        {"customer_id": "CUST-C"},
    ]
    is_syn, count, boost = resolver.evaluate_device_syndicate(dev_id, "CUST-D", past_txns_multi)
    assert is_syn is True
    assert count == 4
    assert boost >= 0.30
