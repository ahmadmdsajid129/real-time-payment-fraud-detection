"""Feature definitions, groupings, and cold-start defaults for the fraud engine."""

from typing import List, Dict, Any

# Complete catalog of all engineered features produced by the pipeline
FEATURE_NAMES: List[str] = [
    # Instant Payload & Temporal
    "amount",
    "log_amount",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_unusual_hour",
    
    # Customer Velocity Sliding Windows
    "txn_count_1m",
    "txn_count_5m",
    "txn_count_15m",
    "txn_count_1h",
    "txn_count_24h",
    "txn_count_7d",
    "amount_sum_5m",
    "amount_sum_1h",
    
    # Customer Behavioral Spending Baselines
    "customer_avg_amount",
    "customer_std_amount",
    "customer_amount_zscore",
    "amount_to_avg_ratio",
    
    # Novelty & Geographic Context
    "is_new_device",
    "is_new_country",
    "is_new_city",
    "unique_merchants_24h",
    "unique_countries_7d",
    "unique_devices_30d",
    
    # Geospatial Kinematics & Velocity
    "time_since_prev_txn",
    "geo_distance_km",
    "travel_speed_kmh",
    "impossible_travel",
    
    # Ecosystem & Entity Sharing
    "device_customer_count",
    "merchant_risk_score",
]

NUMERICAL_FEATURES: List[str] = [
    "amount",
    "log_amount",
    "hour_of_day",
    "day_of_week",
    "txn_count_1m",
    "txn_count_5m",
    "txn_count_15m",
    "txn_count_1h",
    "txn_count_24h",
    "txn_count_7d",
    "amount_sum_5m",
    "amount_sum_1h",
    "customer_avg_amount",
    "customer_std_amount",
    "customer_amount_zscore",
    "amount_to_avg_ratio",
    "unique_merchants_24h",
    "unique_countries_7d",
    "unique_devices_30d",
    "time_since_prev_txn",
    "geo_distance_km",
    "travel_speed_kmh",
    "device_customer_count",
    "merchant_risk_score",
]

BINARY_FEATURES: List[str] = [
    "is_weekend",
    "is_unusual_hour",
    "is_new_device",
    "is_new_country",
    "is_new_city",
    "impossible_travel",
]

# Cold-start defaults applied when a cardholder has no previous transaction history
COLD_START_DEFAULTS: Dict[str, Any] = {
    "txn_count_1m": 0,
    "txn_count_5m": 0,
    "txn_count_15m": 0,
    "txn_count_1h": 0,
    "txn_count_24h": 0,
    "txn_count_7d": 0,
    "amount_sum_5m": 0.0,
    "amount_sum_1h": 0.0,
    "customer_avg_amount": 1500.0,
    "customer_std_amount": 500.0,
    "customer_amount_zscore": 0.0,
    "amount_to_avg_ratio": 1.0,
    "is_new_device": 1,
    "is_new_country": 0,
    "is_new_city": 0,
    "unique_merchants_24h": 0,
    "unique_countries_7d": 1,
    "unique_devices_30d": 1,
    "time_since_prev_txn": 86400.0,  # 24 hours default
    "geo_distance_km": 0.0,
    "travel_speed_kmh": 0.0,
    "impossible_travel": 0,
    "device_customer_count": 1,
    "merchant_risk_score": 0.2,
}
