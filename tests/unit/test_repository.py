"""Unit tests for Database Models and Repository Layer."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.repository import FraudRepository


@pytest.fixture
def db_session():
    """In-memory SQLite session fixture for isolated testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_save_and_retrieve_transaction(db_session):
    repo = FraudRepository(db_session)

    txn_payload = {
        "transaction_id": "TXN-TEST-001",
        "customer_id": "CUST-1001",
        "merchant_id": "MERCH-5001",
        "timestamp": datetime.now(timezone.utc),
        "amount": 149.99,
        "currency": "USD",
        "country": "US",
        "city": "San Francisco",
        "device_id": "DEV-IPHONE-12",
        "payment_method": "apple_pay",
        "idempotency_key": "idemp-001",
    }

    txn = repo.save_transaction(txn_payload)
    assert txn.transaction_id == "TXN-TEST-001"
    assert txn.customer_id == "CUST-1001"

    retrieved = repo.get_transaction("TXN-TEST-001")
    assert retrieved is not None
    assert float(retrieved.amount) == 149.99


def test_prediction_and_risk_decision_flow(db_session):
    repo = FraudRepository(db_session)

    # 1. Save Transaction
    repo.save_transaction({
        "transaction_id": "TXN-TEST-002",
        "customer_id": "CUST-1002",
        "merchant_id": "MERCH-5002",
        "timestamp": datetime.now(timezone.utc),
        "amount": 2500.0,
        "idempotency_key": "idemp-002",
    })

    # 2. Save Prediction
    pred = repo.save_prediction({
        "transaction_id": "TXN-TEST-002",
        "model_version_id": "v1.0.0",
        "raw_score": 2.45,
        "calibrated_probability": 0.88,
        "anomaly_score": 0.75,
        "inference_latency_ms": 3.2,
        "shap_positive_drivers": [("amount", 0.45), ("hour_of_day", 0.22)],
        "shap_negative_drivers": [],
    })
    assert pred.calibrated_probability == 0.88

    # 3. Save Risk Decision
    decision = repo.save_risk_decision({
        "transaction_id": "TXN-TEST-002",
        "risk_score": 82.5,
        "decision": "BLOCK",
        "triggered_rules": ["SUSPICIOUS_HIGH_AMOUNT", "IMPOSSIBLE_TRAVEL"],
        "cost_estimate_fn": 0.0,
        "cost_estimate_fp": 10.0,
    })
    assert decision.decision == "BLOCK"
    assert float(decision.risk_score) == 82.5

    # 4. List Transactions (Hydrated Join)
    txns = repo.list_transactions(limit=10)
    assert len(txns) == 1
    t = txns[0]
    assert t["transaction_id"] == "TXN-TEST-002"
    assert t["decision"] == "BLOCK"
    assert t["risk_score"] == 82.5
    assert len(t["triggered_rules"]) == 2


def test_analyst_feedback_and_kpis(db_session):
    repo = FraudRepository(db_session)

    repo.save_transaction({
        "transaction_id": "TXN-TEST-003",
        "customer_id": "CUST-1003",
        "amount": 90.0,
        "idempotency_key": "idemp-003",
    })
    repo.save_risk_decision({
        "transaction_id": "TXN-TEST-003",
        "risk_score": 15.0,
        "decision": "APPROVE",
    })

    # Record analyst feedback
    feedback = repo.record_analyst_feedback(
        transaction_id="TXN-TEST-003",
        analyst_id="ANALYST-42",
        actual_label="LEGITIMATE",
        notes="Verified cardholder identity via SMS.",
    )
    assert feedback.actual_label == "LEGITIMATE"

    # Verify summary KPIs
    metrics = repo.get_summary_metrics()
    assert metrics["total_transactions"] == 1
    assert metrics["approved_count"] == 1
    assert metrics["blocked_count"] == 0
    assert metrics["total_volume_usd"] == 90.0
