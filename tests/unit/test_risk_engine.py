"""Unit tests for the Risk Engine, Decision Policy, Rules, and Cost Model."""

import pytest
from services.risk_engine.engine import RiskEngine, DecisionEnum
from services.risk_engine.rules import RuleEngine
from services.risk_engine.cost_model import FinancialCostModel


def test_risk_score_bounds_and_clamping():
    """Verify that under any input values (including negatives and extreme numbers),
    risk_score is strictly clamped in [0.0, 100.0]."""
    engine = RiskEngine()

    for p_ml in [-0.5, 0.0, 0.5, 1.0, 1.5]:
        for anom in [-1.0, 0.0, 0.5, 1.0, 2.0]:
            features = {
                "amount": 1000.0,
                "customer_amount_zscore": 10.0,
                "txn_count_1m": 5,
                "impossible_travel": 1,
            }
            decision = engine.evaluate(
                transaction_id="TXN-BOUNDS-TEST",
                amount=1000.0,
                calibrated_ml_prob=p_ml,
                anomaly_score=anom,
                features=features,
            )
            assert 0.0 <= decision.risk_score <= 100.0
            assert decision.decision in [DecisionEnum.APPROVE, DecisionEnum.REVIEW, DecisionEnum.BLOCK]


def test_decision_policy_thresholds():
    engine = RiskEngine(approve_threshold=30.0, block_threshold=75.0)

    # 1. Clean transaction -> APPROVE
    clean_features = {
        "customer_amount_zscore": 0.2,
        "amount_to_avg_ratio": 1.0,
        "txn_count_1m": 0,
        "txn_count_1h": 0,
        "impossible_travel": 0,
        "is_new_device": 0,
        "is_new_country": 0,
        "is_unusual_hour": 0,
    }
    res_approve = engine.evaluate(
        transaction_id="TXN-APP",
        amount=500.0,
        calibrated_ml_prob=0.01,
        anomaly_score=0.05,
        features=clean_features,
    )
    assert res_approve.risk_score < 30.0
    assert res_approve.decision == DecisionEnum.APPROVE

    # 2. Extreme attack -> BLOCK
    attack_features = {
        "customer_amount_zscore": 6.5,
        "amount_to_avg_ratio": 12.0,
        "txn_count_1m": 4,
        "txn_count_1h": 10,
        "impossible_travel": 1,
        "travel_speed_kmh": 1500.0,
        "geo_distance_km": 4000.0,
        "is_new_device": 1,
        "is_new_country": 1,
        "is_unusual_hour": 1,
    }
    res_block = engine.evaluate(
        transaction_id="TXN-BLK",
        amount=65000.0,
        calibrated_ml_prob=0.92,
        anomaly_score=0.88,
        features=attack_features,
    )
    assert res_block.risk_score >= 75.0
    assert res_block.decision == DecisionEnum.BLOCK
    assert len(res_block.triggered_rules) >= 2


def test_rule_engine_triggers():
    rule_engine = RuleEngine()

    # Test Impossible travel rule
    features_travel = {
        "impossible_travel": 1,
        "travel_speed_kmh": 1200.0,
        "geo_distance_km": 3000.0,
    }
    score, rules = rule_engine.evaluate(features_travel)
    assert score >= 0.90
    assert any(r.rule_code == "R01_IMPOSSIBLE_TRAVEL" for r in rules)

    # Test Velocity burst rule
    features_vel = {"txn_count_1m": 4}
    score_v, rules_v = rule_engine.evaluate(features_vel)
    assert any(r.rule_code == "R02_VELOCITY_BURST_1M" for r in rules_v)


def test_financial_cost_model():
    cost_model = FinancialCostModel(
        chargeback_fee=25.0,
        customer_insult_cost=35.0,
        analyst_review_cost=4.0
    )
    costs = cost_model.compute_expected_costs(amount=1000.0, calibrated_prob=0.80)
    # Approve cost: 0.8 * (1000 + 25) = 820.0
    assert costs["expected_cost_approve"] == 820.0
    # Block cost: (1 - 0.8) * 35 = 7.0
    assert costs["expected_cost_block"] == 7.0
