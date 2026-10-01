"""Chaos Engineering & Fault Injection Integration Tests.

Validates system resiliency under simulated component failures:
1. Redis state cache failure / timeout (Degraded feature fallback)
2. ML inference model crash / missing artifacts (Rule-only fallback)
3. Poison pill / malformed message payload (Dead Letter Queue routing)
"""

from datetime import datetime, timezone
import pytest

from services.streaming_client import InMemoryEventBus, StreamProducer, StreamConsumer
from services.feature_service.redis_state import RedisStateManager
from services.feature_service.consumer import FeatureEnrichmentWorker
from services.inference_service.consumer import MLInferenceWorker
from services.risk_engine.engine import RiskEngine
from services.risk_engine.consumer import RiskDecisionWorker


@pytest.fixture(autouse=True)
def reset_event_bus():
    bus = InMemoryEventBus()
    bus.clear()
    yield
    bus.clear()


def test_redis_outage_graceful_degradation():
    """Verify that when Redis connection is broken, feature enrichment defaults safely."""
    # Create an un-connected Redis manager in fallback mode
    unconnected_manager = RedisStateManager(host="non-existent-redis-host", port=9999)
    assert unconnected_manager.is_connected is False

    worker = FeatureEnrichmentWorker(state_manager=unconnected_manager)

    raw_event = {
        "transaction_id": "TXN-CHAOS-001",
        "customer_id": "CUST-CHAOS-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "amount": 199.99,
        "country": "US",
        "city": "Dallas",
        "lat": 32.77,
        "lon": -96.79,
        "device_id": "DEV-CHAOS-1",
        "payment_method": "credit_card",
        "idempotency_key": "idemp-chaos-001",
    }

    # Must NOT raise exception; must compute cold-start safe default features
    enriched = worker.process_message({"value": raw_event})
    assert enriched is not None
    assert "features" in enriched
    assert enriched["features"]["amount"] == 199.99
    assert enriched["features"]["txn_count_1h"] == 0  # Safe cold-start fallback


def test_ml_inference_crash_fallback():
    """Verify that when ML inference model is missing, risk arbitration uses heuristic safety."""
    # Worker with non-existent models directory
    failing_inference_worker = MLInferenceWorker(models_dir="/tmp/non_existent_models")
    assert failing_inference_worker.model is None

    # Evaluate feature vector
    sample_features = {
        "amount": 2500.0,
        "customer_amount_zscore": 3.5,
        "travel_speed_kmh": 0.0,
        "is_new_device": 1,
        "is_new_country": 1,
    }

    evaluated = failing_inference_worker.evaluate_transaction(sample_features)
    assert evaluated is not None
    # Outputs safe fallback score
    assert "calibrated_probability" in evaluated
    assert evaluated["calibrated_probability"] == 0.05

    # Pass to risk engine
    engine = RiskEngine()
    decision = engine.evaluate(
        transaction_id="TXN-CHAOS-002",
        amount=2500.0,
        calibrated_ml_prob=evaluated["calibrated_probability"],
        anomaly_score=evaluated["anomaly_score"],
        features=sample_features,
    )
    assert decision.decision in ["APPROVE", "REVIEW", "BLOCK"]


def test_malformed_payload_dlq_routing():
    """Verify that malformed or poison pill messages are routed to transactions.dlq."""
    bus = InMemoryEventBus()
    worker = FeatureEnrichmentWorker()

    # Broken message missing customer_id and transaction_id
    poison_pill = {
        "amount": "NOT_A_NUMBER",
        "payload": "corrupted_binary_garbage",
    }

    result = worker.process_message({"value": poison_pill})
    assert result is None

    # Check dead letter queue
    dlq_msg = bus.consume("transactions.dlq")
    assert dlq_msg is not None
    assert dlq_msg["value"]["step"] == "feature_enrichment"
    assert "Missing transaction_id or customer_id" in dlq_msg["value"]["error"]
