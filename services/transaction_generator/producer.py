"""Synthetic Payment Transaction Generator and Kafka Stream Publisher.

Publishes payment events to `transactions.raw` with customer_id as partition key,
enforcing FIFO ordering per customer partition.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
import time
from typing import Dict, Any, Optional

from ml.src.data.synthetic_generator import SyntheticTransactionGenerator
from services.streaming_client import StreamProducer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("transaction-generator")


class TransactionStreamProducer:
    """Streams payment transactions to Kafka or local bus at configurable rates."""

    def __init__(self, topic: str = "transactions.raw", producer: Optional[StreamProducer] = None):
        self.topic = topic
        self.producer = producer or StreamProducer()
        self.generator = SyntheticTransactionGenerator(n_customers=500, n_merchants=50, random_state=42)

    def produce_single_transaction(self, scenario: Optional[str] = None) -> Dict[str, Any]:
        """Generates and emits a single transaction."""
        txn = self.generator.generate_single_transaction(scenario=scenario)
        payload = {
            "transaction_id": txn.transaction_id,
            "timestamp": txn.timestamp.isoformat(),
            "customer_id": txn.customer_id,
            "merchant_id": txn.merchant_id,
            "amount": float(txn.amount),
            "currency": txn.currency,
            "country": txn.country,
            "city": txn.city,
            "lat": float(txn.lat),
            "lon": float(txn.lon),
            "device_id": txn.device_id,
            "payment_method": txn.payment_method,
            "ip_address": txn.ip_address,
            "idempotency_key": txn.idempotency_key,
            "ground_truth_fraud": txn.is_fraud,
            "fraud_scenario": txn.fraud_scenario,
        }

        # Keyed by customer_id for partition affinity
        self.producer.send(topic=self.topic, key=txn.customer_id, value=payload)
        logger.info(
            "Emitted TXN: %s | Cust: %s | $%.2f | Fraud: %s (%s)",
            txn.transaction_id,
            txn.customer_id,
            txn.amount,
            txn.is_fraud,
            txn.fraud_scenario or "normal",
        )
        return payload

    def run_stream(self, count: int = 100, rate_per_second: float = 5.0):
        """Continuously streams events at the specified frequency."""
        interval = 1.0 / max(rate_per_second, 0.1)
        logger.info("Starting transaction stream: %d events at %.1f TPS", count, rate_per_second)

        emitted = 0
        while emitted < count:
            self.produce_single_transaction()
            emitted += 1
            time.sleep(interval)

        self.producer.flush()
        logger.info("Stream complete. Total emitted: %d", emitted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transaction Stream Generator")
    parser.add_argument("--count", type=int, default=20, help="Number of transactions to stream")
    parser.add_argument("--rate", type=float, default=2.0, help="Transactions per second")
    args = parser.parse_args()

    producer = TransactionStreamProducer()
    producer.run_stream(count=args.count, rate_per_second=args.rate)
