"""Redis Online Behavioral State Store for Real-Time Feature Enrichment.

Maintains sliding-window counters, sets, and sorted sets (ZSET) for customer history.
Guarantees zero leakage: get_customer_history() retrieves events strictly BEFORE current timestamp.
Supports in-memory fallback mode for local testing without active Redis container.
"""

from datetime import datetime, timezone
import json
from typing import Dict, Any, List, Set, Optional


class RedisStateManager:
    """Manages customer rolling velocity, known entities, and idempotency in Redis."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, redis_client=None):
        self.host = host
        self.port = port
        self.db = db
        self.client = redis_client
        self.is_connected = False

        # In-memory mock storage if Redis connection is unavailable
        self._mock_idemp: Dict[str, float] = {}
        self._mock_windows: Dict[str, List[Dict[str, Any]]] = {}
        self._mock_devices: Dict[str, Set[str]] = {}
        self._mock_countries: Dict[str, Set[str]] = {}
        self._mock_device_txns: Dict[str, List[Dict[str, Any]]] = {}

        self._init_connection()

    def _init_connection(self):
        if self.client is not None:
            self.is_connected = True
            return
        try:
            import redis
            r = redis.Redis(host=self.host, port=self.port, db=self.db, socket_timeout=0.5)
            r.ping()
            self.client = r
            self.is_connected = True
        except Exception:
            # Degrade gracefully to in-memory fallback mode
            self.is_connected = False

    def check_and_set_idempotency(self, idempotency_key: str, ttl_seconds: int = 86400) -> bool:
        """Returns True if the transaction key is NEW; False if it is a DUPLICATE."""
        key = f"idemp:{idempotency_key}"
        if self.is_connected and self.client:
            try:
                # SET key "1" NX EX ttl
                is_new = self.client.set(key, "1", nx=True, ex=ttl_seconds)
                return bool(is_new)
            except Exception:
                pass
        # Fallback in-memory
        if idempotency_key in self._mock_idemp:
            return False
        self._mock_idemp[idempotency_key] = datetime.now(timezone.utc).timestamp()
        return True

    def get_customer_history(self, customer_id: str, before_timestamp_epoch: float) -> List[Dict[str, Any]]:
        """Retrieves past transactions for customer_id strictly timestamped BEFORE before_timestamp_epoch.
        
        Zero Leakage Guarantee: current transaction at t is never returned.
        """
        key = f"cust:{customer_id}:window"
        events = []

        if self.is_connected and self.client:
            try:
                # ZREVRANGEBYSCORE key (before_timestamp_epoch - 1ms) -inf
                # Query strictly smaller score: '(' signifies exclusive bound
                raw_events = self.client.zrevrangebyscore(
                    key,
                    max=f"({before_timestamp_epoch}",
                    min="-inf",
                    start=0,
                    num=100
                )
                for item in raw_events:
                    events.append(json.loads(item.decode("utf-8")))
                return events
            except Exception:
                pass

        # In-memory fallback
        all_hist = self._mock_windows.get(customer_id, [])
        for e in all_hist:
            ts = e["timestamp"]
            ts_epoch = ts.timestamp() if isinstance(ts, datetime) else float(ts)
            if ts_epoch < before_timestamp_epoch:
                events.append(e)
        events.sort(key=lambda x: x["timestamp"] if isinstance(x["timestamp"], (int, float)) else x["timestamp"].timestamp())
        return events

    def get_known_devices(self, customer_id: str) -> Set[str]:
        """Returns set of recognized device IDs for this customer."""
        key = f"cust:{customer_id}:devices"
        if self.is_connected and self.client:
            try:
                members = self.client.smembers(key)
                return {m.decode("utf-8") for m in members}
            except Exception:
                pass
        return self._mock_devices.get(customer_id, set())

    def get_known_countries(self, customer_id: str) -> Set[str]:
        """Returns set of known country codes for this customer."""
        key = f"cust:{customer_id}:countries"
        if self.is_connected and self.client:
            try:
                members = self.client.smembers(key)
                return {m.decode("utf-8") for m in members}
            except Exception:
                pass
        return self._mock_countries.get(customer_id, set())

    def get_device_history(self, device_id: str, before_timestamp_epoch: float) -> List[Dict[str, Any]]:
        """Returns transactions made on this device within 24 hours prior to before_timestamp_epoch."""
        threshold = before_timestamp_epoch - 86400.0
        all_dev_txns = self._mock_device_txns.get(device_id, [])
        valid = []
        for d in all_dev_txns:
            ts_epoch = d["timestamp"].timestamp() if isinstance(d["timestamp"], datetime) else float(d["timestamp"])
            if threshold <= ts_epoch < before_timestamp_epoch:
                valid.append(d)
        return valid

    def update_state_post_decision(self, txn_payload: Dict[str, Any]) -> None:
        """Appends the evaluated transaction to Redis state.
        
        Called exclusively AFTER risk scoring is finalized.
        """
        cust_id = txn_payload["customer_id"]
        dev_id = txn_payload["device_id"]
        country = txn_payload["country"]
        ts = txn_payload["timestamp"]
        ts_epoch = ts.timestamp() if isinstance(ts, datetime) else float(ts)

        item_dict = {
            "timestamp": ts,
            "amount": float(txn_payload["amount"]),
            "lat": float(txn_payload["lat"]),
            "lon": float(txn_payload["lon"]),
            "country": country,
            "city": str(txn_payload.get("city", "")),
            "merchant_id": str(txn_payload.get("merchant_id", "")),
            "device_id": dev_id,
            "customer_id": cust_id,
        }

        if self.is_connected and self.client:
            try:
                # Add to Sorted Set
                pipe = self.client.pipeline()
                window_key = f"cust:{cust_id}:window"
                pipe.zadd(window_key, {json.dumps(item_dict, default=str): ts_epoch})
                pipe.expire(window_key, 2592000)  # 30 days TTL

                # Add to sets
                pipe.sadd(f"cust:{cust_id}:devices", dev_id)
                pipe.expire(f"cust:{cust_id}:devices", 7776000)  # 90 days TTL

                pipe.sadd(f"cust:{cust_id}:countries", country)
                pipe.expire(f"cust:{cust_id}:countries", 7776000)

                pipe.execute()
                return
            except Exception:
                pass

        # In-memory fallback
        if cust_id not in self._mock_windows:
            self._mock_windows[cust_id] = []
        self._mock_windows[cust_id].append(item_dict)

        if cust_id not in self._mock_devices:
            self._mock_devices[cust_id] = set()
        self._mock_devices[cust_id].add(dev_id)

        if cust_id not in self._mock_countries:
            self._mock_countries[cust_id] = set()
        self._mock_countries[cust_id].add(country)

        if dev_id not in self._mock_device_txns:
            self._mock_device_txns[dev_id] = []
        self._mock_device_txns[dev_id].append(item_dict)
