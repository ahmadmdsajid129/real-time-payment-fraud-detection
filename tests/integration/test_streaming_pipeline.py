"""End-to-End Streaming Pipeline Integration Test.

Tests the full event flow across topics:
transactions.raw -> transactions.features -> transactions.predictions -> transactions.decisions
verifying zero data leakage, state persistence, idempotency, and risk arbitration.
"""

from datetime import datetime, timezone
import pytest

from services.streaming_client import InMemoryEventBus, StreamProducer, StreamConsumer
from services.feature_service.redis_state import RedisStateManager
from services.feature_service.consumer import FeatureEnrichmentWorker
from services.inference_service.consumer import MLInferenceWorker
from services.risk_engine.consumer import RiskDecisionWorker
from database.connection import get_db_context, init_db
from database.repository import FraudRepository


@pytest.fixture(autouse=True)
def clean_environment():
    """Reset the in-memory event bus and database before each test."""
    bus = InMemoryEventBus()
    bus.clear()
    init_db()
    yield
    bus.clear()


def test_full_streaming_pipeline_flow():
    """Verifies complete streaming pipeline from raw event to final decision and persistence."""
    bus = InMemoryEventBus()
    state_manager = RedisStateManager()

    # 1. Setup workers connected to the shared event bus
    feature_worker = FeatureEnrichmentWorker(state_manager=state_manager)
    inference_worker = MLInferenceWorker()
    risk_worker = RiskDecisionWorker(state_manager=state_manager)

    # 2. Simulate producer publishing a raw transaction
    raw_producer = StreamProducer()
    txn_id = "TXN-STREAM-001"
    cust_id = "CUST-STREAM-101"
    raw_event = {
        "transaction_id": txn_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": cust_id,
        "merchant_id": "MERCH-9999",
        "amount": 250.0,
        "currency": "USD",
        "country": "US",
        "city": "New York",
        "lat": 40.7128,
        "lon": -74.0060,
        "device_id": "DEV-STREAM-1",
        "payment_method": "credit_card",
        "ip_address": "192.168.1.1",
        "idempotency_key": "idemp-stream-001",
    }

    raw_producer.send("transactions.raw", key=cust_id, value=raw_event)

    # 3. Step 1: Feature Enrichment Worker consumes raw and emits features
    raw_msg = bus.consume("transactions.raw")
    assert raw_msg is not None
    enriched_event = feature_worker.process_message(raw_msg)
    assert enriched_event is not None
    assert "features" in enriched_event
    assert enriched_event["features"]["amount"] == 250.0

    # 4. Step 2: ML Inference Worker consumes features and emits predictions
    feat_msg = bus.consume("transactions.features")
    assert feat_msg is not None
    predicted_event = inference_worker.process_message(feat_msg)
    assert predicted_event is not None
    assert "model_outputs" in predicted_event
    outputs = predicted_event["model_outputs"]
    assert "calibrated_probability" in outputs
    assert "anomaly_score" in outputs
    assert 0.0 <= outputs["calibrated_probability"] <= 1.0
    assert outputs["inference_latency_ms"] >= 0.0

    # 5. Step 3: Risk Decision Worker consumes predictions and emits decisions
    pred_msg = bus.consume("transactions.predictions")
    assert pred_msg is not None
    final_decision = risk_worker.process_message(pred_msg)
    assert final_decision is not None
    assert final_decision["transaction_id"] == txn_id
    assert final_decision["decision"] in ["APPROVE", "REVIEW", "BLOCK"]
    assert 0.0 <= final_decision["risk_score"] <= 100.0

    # 6. Verify decision message reached transactions.decisions
    decision_msg = bus.consume("transactions.decisions")
    assert decision_msg is not None
    assert decision_msg["value"]["transaction_id"] == txn_id

    # 7. Verify Redis state post-decision update (Zero Leakage verification)
    # The transaction MUST be in Redis state now for future transactions
    history_after = state_manager.get_customer_history(cust_id, before_timestamp_epoch=datetime.now(timezone.utc).timestamp() + 10.0)
    assert len(history_after) == 1
    assert history_after[0]["amount"] == 250.0

    # 8. Verify Database Persistence
    with get_db_context() as session:
        repo = FraudRepository(session)
        persisted_txn = repo.get_transaction(txn_id)
        assert persisted_txn is not None
        assert float(persisted_txn.amount) == 250.0
        assert persisted_txn.risk_decision.decision in ["APPROVE", "REVIEW", "BLOCK"]
        assert persisted_txn.prediction.calibrated_probability == outputs["calibrated_probability"]


def test_duplicate_idempotency_prevention():
    """Verifies that replaying an identical idempotency key is rejected at the feature boundary."""
    bus = InMemoryEventBus()
    state_manager = RedisStateManager()
    feature_worker = FeatureEnrichmentWorker(state_manager=state_manager)

    raw_event = {
        "transaction_id": "TXN-IDEMP-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": "CUST-IDEMP-01",
        "amount": 50.0,
        "lat": 37.77,
        "lon": -122.41,
        "country": "US",
        "city": "San Francisco",
        "device_id": "DEV-IDEMP-1",
        "idempotency_key": "key-idemp-unique-999",
    }

    # First delivery: processed
    first_res = feature_worker.process_message({"value": raw_event})
    assert first_res is not None

    # Second delivery (replay attack or network duplicate): dropped
    second_res = feature_worker.process_message({"value": raw_event})
    assert second_res is None
