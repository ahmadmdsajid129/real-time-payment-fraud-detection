"""Unit tests for FastAPI REST API endpoints using TestClient."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import models  # noqa: F401
from database.connection import Base, get_db
from services.api.main import app

# In-memory test database fixture with StaticPool for connection sharing
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Real-Time Payment Fraud Detection" in data["service"]
    assert data["version"] == "1.0.0"


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
    assert data["dependencies"]["champion_model_loaded"] is True


def test_synchronous_score_and_idempotency():
    txn_id = "TXN-API-TEST-001"
    payload = {
        "transaction_id": txn_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": "CUST-API-101",
        "merchant_id": "MERCH-9999",
        "amount": 125.50,
        "currency": "USD",
        "country": "US",
        "city": "Boston",
        "lat": 42.36,
        "lon": -71.05,
        "device_id": "DEV-TEST-01",
        "payment_method": "credit_card",
        "ip_address": "192.168.1.100",
        "idempotency_key": "idemp-api-001",
    }

    # 1. First evaluation: should succeed with 200
    res = client.post("/api/v1/transactions/score", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["transaction_id"] == txn_id
    assert data["decision"] in ["APPROVE", "REVIEW", "BLOCK"]
    assert 0.0 <= data["risk_score"] <= 100.0
    assert 0.0 <= data["calibrated_fraud_probability"] <= 1.0
    assert "latency_breakdown_ms" in data
    assert data["latency_breakdown_ms"]["total"] > 0.0

    # 2. Duplicate evaluation: should be rejected with 409 Conflict
    dup_res = client.post("/api/v1/transactions/score", json=payload)
    assert dup_res.status_code == 409
    assert "Duplicate transaction" in dup_res.json()["detail"]


def test_transaction_detail_and_explanation():
    txn_id = "TXN-API-TEST-002"
    payload = {
        "transaction_id": txn_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": "CUST-API-102",
        "merchant_id": "MERCH-9999",
        "amount": 2500.00,
        "country": "US",
        "city": "Boston",
        "device_id": "DEV-TEST-02",
        "idempotency_key": "idemp-api-002",
    }
    # Score transaction first
    score_res = client.post("/api/v1/transactions/score", json=payload)
    assert score_res.status_code == 200

    # 1. Detail endpoint
    detail_res = client.get(f"/api/v1/transactions/{txn_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["transaction_id"] == txn_id
    assert detail["amount"] == 2500.00
    assert detail["decision"] in ["APPROVE", "REVIEW", "BLOCK"]

    # 2. Explanation endpoint
    expl_res = client.get(f"/api/v1/transactions/{txn_id}/explanation")
    assert expl_res.status_code == 200
    expl = expl_res.json()
    assert expl["transaction_id"] == txn_id
    assert "top_positive_features" in expl
    assert "top_negative_features" in expl


def test_customer_profile_and_dashboard():
    # Customer profile
    prof_res = client.get("/api/v1/customers/CUST-API-101/profile")
    assert prof_res.status_code == 200
    prof = prof_res.json()
    assert prof["customer_id"] == "CUST-API-101"
    assert "recent_velocity" in prof

    # Dashboard Summary
    summary_res = client.get("/api/v1/dashboard/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_transactions"] >= 2
    assert "decisions" in summary

    # Recent Transactions
    rec_res = client.get("/api/v1/dashboard/recent-transactions?limit=10")
    assert rec_res.status_code == 200
    assert isinstance(rec_res.json(), list)

    # Risk Distribution
    dist_res = client.get("/api/v1/dashboard/risk-distribution")
    assert dist_res.status_code == 200
    assert isinstance(dist_res.json(), list)


def test_analyst_feedback_submission():
    feedback_payload = {
        "transaction_id": "TXN-API-TEST-001",
        "analyst_id": "ANALYST-SENIOR-1",
        "actual_label": "LEGITIMATE",
        "notes": "Customer confirmed transaction over phone.",
    }
    fb_res = client.post("/api/v1/feedback", json=feedback_payload)
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["status"] == "RECORDED"
    assert fb_data["actual_label"] == "LEGITIMATE"


def test_prometheus_metrics_endpoint():
    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
