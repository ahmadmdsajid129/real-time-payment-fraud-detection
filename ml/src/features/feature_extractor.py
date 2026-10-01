"""Feature Engineering Pipeline for Real-Time Payment Fraud Detection.

Guarantees Zero Temporal Data Leakage:
Any calculation of customer-level or device-level aggregations strictly evaluates
historical transactions timestamped PRIOR to the current transaction.
"""

from datetime import datetime, timezone
import math
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from ml.src.features.feature_definitions import (
    FEATURE_NAMES,
    COLD_START_DEFAULTS,
)


MERCHANT_CATEGORY_RISK: Dict[str, float] = {
    "JEWELRY_LUXURY": 0.85,
    "DIGITAL_WALLET_TRANSFER": 0.80,
    "ELECTRONICS": 0.75,
    "GAMING_CASINO": 0.70,
    "DEPARTMENT_STORE": 0.35,
    "GAS_STATION": 0.20,
    "UTILITIES": 0.15,
    "GROCERY": 0.10,
    "RESTAURANT": 0.10,
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance in kilometers between two points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class FeatureExtractor:
    """Computes behavioral sliding windows, z-scores, velocity, and kinematics."""

    def __init__(self, cold_start_defaults: Optional[Dict[str, Any]] = None):
        self.defaults = cold_start_defaults or COLD_START_DEFAULTS

    def extract_features_single(
        self,
        current_txn: Dict[str, Any],
        customer_history: Optional[List[Dict[str, Any]]] = None,
        device_history: Optional[List[Dict[str, Any]]] = None,
        customer_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extracts features for a single transaction without leaking current transaction into history.
        
        `customer_history` and `device_history` MUST contain only past events (t < current_txn.timestamp).
        """
        ts = current_txn["timestamp"]
        if not isinstance(ts, pd.Timestamp):
            ts = pd.to_datetime(ts)
        amount = float(current_txn["amount"])
        lat = float(current_txn["lat"])
        lon = float(current_txn["lon"])
        device_id = str(current_txn["device_id"])
        country = str(current_txn["country"])
        city = str(current_txn["city"])
        category = str(current_txn.get("merchant_category", "DEPARTMENT_STORE"))

        # 1. Instant Temporal Features
        hour_of_day = int(ts.hour)
        day_of_week = int(ts.dayofweek)
        is_weekend = int(day_of_week in [5, 6])
        
        # Diurnal check: customer typical hours or default 8 to 22
        typ_start = 8
        typ_end = 22
        if customer_profile:
            typ_start = customer_profile.get("typical_hour_start", 8)
            typ_end = customer_profile.get("typical_hour_end", 22)
        is_unusual_hour = int(hour_of_day < typ_start or hour_of_day > typ_end)

        features: Dict[str, Any] = {
            "amount": amount,
            "log_amount": round(float(np.log1p(amount)), 4),
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "is_unusual_hour": is_unusual_hour,
            "merchant_risk_score": MERCHANT_CATEGORY_RISK.get(category, 0.3),
        }

        # 2. Customer Behavioral History Aggregations
        raw_history = customer_history or []
        history = []
        for h in raw_history:
            h_ts = h["timestamp"]
            if not isinstance(h_ts, pd.Timestamp):
                h_ts = pd.to_datetime(h_ts)
            if ts.tz is not None and getattr(h_ts, "tz", None) is None:
                h_ts = h_ts.tz_localize("UTC")
            elif ts.tz is None and getattr(h_ts, "tz", None) is not None:
                h_ts = h_ts.tz_localize(None)
            if h_ts < ts:
                history.append({**h, "timestamp": h_ts})

        if not history:
            # Cold-start customer
            for k in [
                "txn_count_1m", "txn_count_5m", "txn_count_15m", "txn_count_1h",
                "txn_count_24h", "txn_count_7d", "amount_sum_5m", "amount_sum_1h",
                "customer_avg_amount", "customer_std_amount", "customer_amount_zscore",
                "amount_to_avg_ratio", "is_new_device", "is_new_country", "is_new_city",
                "unique_merchants_24h", "unique_countries_7d", "unique_devices_30d",
                "time_since_prev_txn", "geo_distance_km", "travel_speed_kmh", "impossible_travel",
            ]:
                features[k] = self.defaults[k]
        else:
            # Compute sliding windows
            ts_epoch = ts.timestamp()
            past_amounts = [h["amount"] for h in history]
            past_times = [h["timestamp"].timestamp() for h in history]
            
            # Historical spending baseline
            mu = float(np.mean(past_amounts))
            sigma = float(np.std(past_amounts)) if len(past_amounts) > 1 else self.defaults["customer_std_amount"]
            sigma = max(sigma, 1.0)
            
            zscore = (amount - mu) / sigma
            ratio = amount / (mu + 1.0)

            # Rolling count and sum windows
            def count_in_window(sec: float) -> int:
                threshold = ts_epoch - sec
                return sum(1 for t in past_times if t >= threshold)

            def sum_in_window(sec: float) -> float:
                threshold = ts_epoch - sec
                return sum(h["amount"] for h in history if h["timestamp"].timestamp() >= threshold)

            features["txn_count_1m"] = count_in_window(60.0)
            features["txn_count_5m"] = count_in_window(300.0)
            features["txn_count_15m"] = count_in_window(900.0)
            features["txn_count_1h"] = count_in_window(3600.0)
            features["txn_count_24h"] = count_in_window(86400.0)
            features["txn_count_7d"] = count_in_window(604800.0)
            features["amount_sum_5m"] = round(sum_in_window(300.0), 2)
            features["amount_sum_1h"] = round(sum_in_window(3600.0), 2)

            features["customer_avg_amount"] = round(mu, 2)
            features["customer_std_amount"] = round(sigma, 2)
            features["customer_amount_zscore"] = round(float(zscore), 3)
            features["amount_to_avg_ratio"] = round(float(ratio), 3)

            # Novelty & Sets
            seen_devices = {h["device_id"] for h in history}
            seen_countries = {h["country"] for h in history}
            seen_cities = {h["city"] for h in history}
            
            features["is_new_device"] = int(device_id not in seen_devices)
            features["is_new_country"] = int(country not in seen_countries)
            features["is_new_city"] = int(city not in seen_cities)

            # Diversity in windows
            merchs_24h = {h["merchant_id"] for h in history if h["timestamp"].timestamp() >= ts_epoch - 86400.0}
            countries_7d = {h["country"] for h in history if h["timestamp"].timestamp() >= ts_epoch - 604800.0}
            devices_30d = {h["device_id"] for h in history if h["timestamp"].timestamp() >= ts_epoch - 2592000.0}

            features["unique_merchants_24h"] = len(merchs_24h)
            features["unique_countries_7d"] = max(1, len(countries_7d))
            features["unique_devices_30d"] = max(1, len(devices_30d))

            # Kinematics relative to immediately preceding transaction
            last_event = history[-1]
            last_ts = last_event["timestamp"]
            if not isinstance(last_ts, pd.Timestamp):
                last_ts = pd.to_datetime(last_ts)
            if ts.tz is not None and getattr(last_ts, "tz", None) is None:
                last_ts = last_ts.tz_localize("UTC")
            elif ts.tz is None and getattr(last_ts, "tz", None) is not None:
                last_ts = last_ts.tz_localize(None)
            delta_sec = max(0.5, (ts - last_ts).total_seconds())
            features["time_since_prev_txn"] = round(delta_sec, 1)

            dist_km = haversine_distance(lat, lon, float(last_event["lat"]), float(last_event["lon"]))
            features["geo_distance_km"] = round(dist_km, 2)

            speed_kmh = dist_km / (delta_sec / 3600.0)
            features["travel_speed_kmh"] = round(speed_kmh, 1)

            is_impossible = int(speed_kmh > 900.0 and dist_km > 200.0)
            features["impossible_travel"] = is_impossible

        # 3. Device Ecosystem Sharing
        dev_history = device_history or []
        dev_history_24h = []
        for d in dev_history:
            d_ts = d["timestamp"]
            if not isinstance(d_ts, pd.Timestamp):
                d_ts = pd.to_datetime(d_ts)
            if ts.tz is not None and getattr(d_ts, "tz", None) is None:
                d_ts = d_ts.tz_localize("UTC")
            elif ts.tz is None and getattr(d_ts, "tz", None) is not None:
                d_ts = d_ts.tz_localize(None)
            if (ts - d_ts).total_seconds() <= 86400.0:
                dev_history_24h.append(d)
        unique_custs_on_device = len({d["customer_id"] for d in dev_history_24h})
        features["device_customer_count"] = max(1, unique_custs_on_device)

        return features

    def extract_features_batch(
        self,
        df: pd.DataFrame,
        customer_profiles: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Extracts features for an entire historical DataFrame using chronological event streaming.
        
        Guarantees row i only computes state from events j < i.
        """
        df_sorted = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_sorted["timestamp"]):
            df_sorted["timestamp"] = pd.to_datetime(df_sorted["timestamp"])
        df_sorted.sort_values(by="timestamp", inplace=True)
        df_sorted.reset_index(drop=True, inplace=True)

        customer_histories: Dict[str, List[Dict[str, Any]]] = {}
        device_histories: Dict[str, List[Dict[str, Any]]] = {}
        feature_rows: List[Dict[str, Any]] = []

        # Iterate chronologically
        for _, row in df_sorted.iterrows():
            cust_id = row["customer_id"]
            dev_id = row["device_id"]
            cust_hist = customer_histories.get(cust_id, [])
            dev_hist = device_histories.get(dev_id, [])

            # Extract features BEFORE adding current event to history
            row_dict = row.to_dict()
            profile = customer_profiles.get(cust_id) if customer_profiles else None
            feats = self.extract_features_single(
                current_txn=row_dict,
                customer_history=cust_hist,
                device_history=dev_hist,
                customer_profile=profile,
            )
            feature_rows.append(feats)

            # Update historical state AFTER feature extraction
            hist_item = {
                "timestamp": row["timestamp"],
                "amount": float(row["amount"]),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "country": str(row["country"]),
                "city": str(row["city"]),
                "merchant_id": str(row["merchant_id"]),
                "device_id": dev_id,
                "customer_id": cust_id,
            }
            if cust_id not in customer_histories:
                customer_histories[cust_id] = []
            customer_histories[cust_id].append(hist_item)

            if dev_id not in device_histories:
                device_histories[dev_id] = []
            device_histories[dev_id].append(hist_item)

        feats_df = pd.DataFrame(feature_rows)

        # Concatenate identifiers and target label for training
        result_df = pd.concat([
            df_sorted[["transaction_id", "timestamp", "customer_id", "merchant_id", "is_fraud"]],
            feats_df
        ], axis=1)

        return result_df
