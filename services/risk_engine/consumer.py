"""Risk Decisioning, Persistence & State Commit Consumer Worker.

Listens to `transactions.predictions`, arbitrates multi-factor risk scores,
persists records to PostgreSQL, commits post-decision transaction state to Redis,
and publishes finalized decisions to `transactions.decisions`.
"""

from datetime import datetime, timezone
import json
import logging
import os
import time
from typing import Dict, Any, Optional

from database.connection import get_db_context, init_db
from database.repository import FraudRepository
from services.feature_service.redis_state import RedisStateManager
from services.risk_engine.engine import RiskEngine
from services.streaming_client import StreamConsumer, StreamProducer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("risk-consumer")


class RiskDecisionWorker:
    """Consumes ML model outputs, applies risk policy, persists trace, and updates online state."""

    def __init__(
        self,
        consumer: Optional[StreamConsumer] = None,
        producer: Optional[StreamProducer] = None,
        risk_engine: Optional[RiskEngine] = None,
        state_manager: Optional[RedisStateManager] = None,
    ):
        self.consumer = consumer or StreamConsumer(
            topic="transactions.predictions",
            group_id=os.getenv("KAFKA_CONSUMER_GROUP_DECISIONS", "risk-decision-group"),
        )
        self.producer = producer or StreamProducer()
        self.risk_engine = risk_engine or RiskEngine()
        self.state_manager = state_manager or RedisStateManager()

        # Initialize database tables if needed
        try:
            init_db()
        except Exception as e:
            logger.warning("Database init check: %s", e)

    def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a single predicted transaction event."""
        payload = message.get("value", message)
        txn_id = payload.get("transaction_id")
        cust_id = payload.get("customer_id")
        amount = float(payload.get("amount", 0.0))
        features = payload.get("features", {})
        outputs = payload.get("model_outputs", {})

        if not txn_id or not outputs:
            logger.warning("Invalid prediction message: %s", payload)
            self.consumer.route_error(payload, "Missing model_outputs or transaction_id", "risk_engine")
            return None

        calib_prob = float(outputs.get("calibrated_probability", 0.0))
        anom_score = float(outputs.get("anomaly_score", 0.0))

        # 1. Multi-Factor Risk Arbitration
        decision = self.risk_engine.evaluate(
            transaction_id=txn_id,
            amount=amount,
            calibrated_ml_prob=calib_prob,
            anomaly_score=anom_score,
            features=features,
        )

        triggered_rules_serialized = [
            {"rule_id": r.rule_id, "name": r.rule_name, "severity": r.severity, "weight": r.weight}
            for r in decision.triggered_rules
        ]

        # 2. Database Persistence (PostgreSQL / SQLite fallback)
        try:
            with get_db_context() as db_session:
                repo = FraudRepository(db_session)

                # Persist Transaction
                repo.save_transaction({
                    "transaction_id": txn_id,
                    "timestamp": payload["timestamp"],
                    "customer_id": cust_id,
                    "merchant_id": payload.get("merchant_id", "MERCH-0001"),
                    "amount": amount,
                    "currency": payload.get("currency", "USD"),
                    "country": payload.get("country", "US"),
                    "city": payload.get("city", "Unknown"),
                    "device_id": payload.get("device_id", "DEV-UNKNOWN"),
                    "payment_method": payload.get("payment_method", "credit_card"),
                    "ip_address": payload.get("ip_address"),
                    "idempotency_key": payload.get("idempotency_key", txn_id),
                })

                # Persist Prediction
                repo.save_prediction({
                    "transaction_id": txn_id,
                    "model_version_id": outputs.get("model_version_id", "v1.0.0"),
                    "raw_score": outputs.get("raw_score", 0.0),
                    "calibrated_probability": calib_prob,
                    "anomaly_score": anom_score,
                    "inference_latency_ms": outputs.get("inference_latency_ms", 1.0),
                    "shap_positive_drivers": outputs.get("shap_positive_drivers", []),
                    "shap_negative_drivers": outputs.get("shap_negative_drivers", []),
                    "feature_payload": features,
                })

                # Persist Decision
                repo.save_risk_decision({
                    "transaction_id": txn_id,
                    "risk_score": decision.risk_score,
                    "decision": decision.decision.value,
                    "triggered_rules": triggered_rules_serialized,
                    "cost_estimate_fn": decision.expected_costs.get("cost_of_false_negative", 0.0),
                    "cost_estimate_fp": decision.expected_costs.get("cost_of_false_positive", 0.0),
                    "status": "FINAL",
                })
        except Exception as e:
            logger.error("DB persistence error for txn %s: %s", txn_id, e)

        # 3. Post-Decision State Update (Redis)
        # Guarantees zero leakage: past transactions only updated AFTER decisioning
        self.state_manager.update_state_post_decision(payload)

        # 4. Form Final Decision Event
        final_event = {
            "transaction_id": txn_id,
            "customer_id": cust_id,
            "amount": amount,
            "timestamp": payload["timestamp"],
            "risk_score": decision.risk_score,
            "decision": decision.decision.value,
            "calibrated_probability": calib_prob,
            "anomaly_score": anom_score,
            "behavioral_score": decision.behavioral_score,
            "rule_score": decision.rule_score,
            "triggered_rules": triggered_rules_serialized,
            "behavioral_signals": decision.behavioral_signals,
            "expected_costs": decision.expected_costs,
            "shap_positive_drivers": outputs.get("shap_positive_drivers", []),
            "shap_negative_drivers": outputs.get("shap_negative_drivers", []),
            "inference_latency_ms": outputs.get("inference_latency_ms", 0.0),
            "finalized_at": datetime.now(timezone.utc).isoformat(),
        }

        # 5. Emit to Downstream Topic (transactions.decisions)
        self.producer.send(
            topic="transactions.decisions",
            key=cust_id,
            value=final_event,
        )

        logger.info(
            "DECISION for TXN %s | %s | Risk: %.1f | Rules: %d",
            txn_id,
            decision.decision.value,
            decision.risk_score,
            len(decision.triggered_rules),
        )

        self.consumer.commit(message.get("raw"))
        return final_event

    def run_worker_poll(self, max_messages: Optional[int] = None):
        """Worker loop polling events on transactions.predictions."""
        logger.info("Risk Decision worker started. Awaiting events on transactions.predictions...")
        processed = 0
        while max_messages is None or processed < max_messages:
            msg = self.consumer.poll(timeout_sec=0.5)
            if msg:
                self.process_message(msg)
                processed += 1
            else:
                time.sleep(0.05)


if __name__ == "__main__":
    worker = RiskDecisionWorker()
    worker.run_worker_poll()
