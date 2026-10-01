"""Real-Time Feature Enrichment Consumer Worker.

Listens to `transactions.raw`, retrieves online behavioral history from Redis
with strict zero-leakage guarantees, computes kinematic and rolling features,
and publishes enriched payloads to `transactions.features`.
"""

from datetime import datetime, timezone
import json
import logging
import os
import time
from typing import Dict, Any, Optional

import pandas as pd
from ml.src.features.feature_extractor import FeatureExtractor
from services.feature_service.redis_state import RedisStateManager
from services.streaming_client import StreamConsumer, StreamProducer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("feature-service")


class FeatureEnrichmentWorker:
    """Enriches incoming transaction events with real-time behavioral features."""

    def __init__(
        self,
        consumer: Optional[StreamConsumer] = None,
        producer: Optional[StreamProducer] = None,
        state_manager: Optional[RedisStateManager] = None,
    ):
        self.consumer = consumer or StreamConsumer(
            topic="transactions.raw",
            group_id=os.getenv("KAFKA_CONSUMER_GROUP_FEATURES", "feature-enrichment-group"),
        )
        self.producer = producer or StreamProducer()
        self.state_manager = state_manager or RedisStateManager()
        self.extractor = FeatureExtractor()

    def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a single raw transaction message."""
        payload = message.get("value", message)
        txn_id = payload.get("transaction_id")
        cust_id = payload.get("customer_id")
        idemp_key = payload.get("idempotency_key", txn_id)

        if not txn_id or not cust_id:
            logger.warning("Invalid raw message payload: %s", payload)
            self.consumer.route_error(payload, "Missing transaction_id or customer_id", "feature_enrichment")
            return None

        # 1. Idempotency Check
        if not self.state_manager.check_and_set_idempotency(idemp_key):
            logger.warning("Duplicate transaction dropped: %s (idemp: %s)", txn_id, idemp_key)
            return None

        # 2. Parse Timestamp and Query Zero-Leakage Past History
        ts_val = payload["timestamp"]
        if isinstance(ts_val, str):
            ts = pd.to_datetime(ts_val)
        else:
            ts = pd.to_datetime(ts_val)
        ts_epoch = ts.timestamp()

        # Query past customer events (strictly before ts_epoch)
        raw_cust_hist = self.state_manager.get_customer_history(cust_id, before_timestamp_epoch=ts_epoch)
        cust_hist = []
        for h in raw_cust_hist:
            h_ts = h["timestamp"]
            if isinstance(h_ts, str):
                h_ts = pd.to_datetime(h_ts)
            elif isinstance(h_ts, (int, float)):
                h_ts = pd.to_datetime(h_ts, unit="s", utc=True)
            cust_hist.append({
                **h,
                "timestamp": h_ts,
                "amount": float(h["amount"]),
                "lat": float(h["lat"]),
                "lon": float(h["lon"]),
                "device_id": str(h.get("device_id", "")),
                "country": str(h.get("country", "")),
                "city": str(h.get("city", "")),
                "merchant_id": str(h.get("merchant_id", "")),
            })

        # Query past device events
        raw_dev_hist = self.state_manager.get_device_history(payload.get("device_id", ""), before_timestamp_epoch=ts_epoch)
        dev_hist = []
        for d in raw_dev_hist:
            d_ts = d["timestamp"]
            if isinstance(d_ts, str):
                d_ts = pd.to_datetime(d_ts)
            elif isinstance(d_ts, (int, float)):
                d_ts = pd.to_datetime(d_ts, unit="s", utc=True)
            dev_hist.append({
                **d,
                "timestamp": d_ts,
                "customer_id": d.get("customer_id", ""),
            })

        # 3. Extract Online Real-Time Features
        features = self.extractor.extract_features_single(
            current_txn=payload,
            customer_history=cust_hist,
            device_history=dev_hist,
        )

        # 4. Form Enriched Payload
        enriched_event = {
            **payload,
            "features": features,
            "feature_computed_at": datetime.now(timezone.utc).isoformat(),
        }

        # 5. Emit to Downstream Topic (transactions.features)
        self.producer.send(
            topic="transactions.features",
            key=cust_id,
            value=enriched_event,
        )
        logger.info(
            "Enriched TXN %s | Cust: %s | 1h Count: %d | Speed: %.1f km/h",
            txn_id,
            cust_id,
            features.get("txn_count_1h", 0),
            features.get("travel_speed_kmh", 0.0),
        )

        self.consumer.commit(message.get("raw"))
        return enriched_event

    def run_worker_poll(self, max_messages: Optional[int] = None):
        """Worker loop polling and processing raw events."""
        logger.info("Feature enrichment worker started. Awaiting events on transactions.raw...")
        processed = 0
        while max_messages is None or processed < max_messages:
            msg = self.consumer.poll(timeout_sec=0.5)
            if msg:
                self.process_message(msg)
                processed += 1
            else:
                time.sleep(0.05)


if __name__ == "__main__":
    worker = FeatureEnrichmentWorker()
    worker.run_worker_poll()
