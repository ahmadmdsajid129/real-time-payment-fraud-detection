"""Behavioral Profiler & Behavioral Risk Signal Synthesizer.

Computes a normalized [0.0, 1.0] behavioral deviation risk score combining
spending z-scores, velocity spikes, spatial kinematics, and novelty signals.
"""

from typing import Dict, Any, List, Tuple


class BehavioralProfiler:
    """Synthesizes customer behavioral deviations into a normalized [0.0, 1.0] risk signal."""

    @staticmethod
    def score_behavior(features: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Calculates normalized behavioral volatility score and triggered signal codes.
        
        Returns:
            (score: float in [0.0, 1.0], triggered_signals: List[str])
        """
        triggered_signals: List[str] = []

        # 1. Amount Z-score deviation (normal behavior Z in [-2, 2])
        zscore = float(features.get("customer_amount_zscore", 0.0))
        ratio = float(features.get("amount_to_avg_ratio", 1.0))
        sz = 0.0
        if zscore > 2.0 or ratio > 3.0:
            sz = min(1.0, max(0.0, (zscore - 1.5) / 3.5))
            triggered_signals.append("AMOUNT_HIGH_ZSCORE")
        if ratio > 8.0:
            sz = max(sz, 0.85)
            triggered_signals.append("AMOUNT_RATIO_SURGE")

        # 2. Velocity burst deviation
        v1m = int(features.get("txn_count_1m", 0))
        v1h = int(features.get("txn_count_1h", 0))
        sv = min(1.0, (v1m * 0.45) + (max(0, v1h - 3) * 0.10))
        if v1m >= 2:
            triggered_signals.append("VELOCITY_BURST_1M")
        if v1h >= 5:
            triggered_signals.append("VELOCITY_ELEVATED_1H")

        # 3. Kinematics & Geospatial travel
        speed = float(features.get("travel_speed_kmh", 0.0))
        impossible = int(features.get("impossible_travel", 0))
        sk = 0.0
        if impossible == 1:
            sk = 1.0
            triggered_signals.append("IMPOSSIBLE_TRAVEL_SPEED")
        elif speed > 500.0:
            sk = min(1.0, speed / 900.0)
            triggered_signals.append("HIGH_TRANSIT_VELOCITY")

        # 4. Novelty & Entity Sets
        new_dev = int(features.get("is_new_device", 0))
        new_country = int(features.get("is_new_country", 0))
        new_city = int(features.get("is_new_city", 0))
        sn = (0.4 * new_dev) + (0.4 * new_country) + (0.2 * new_city)
        if new_dev:
            triggered_signals.append("NEW_DEVICE_DETECTED")
        if new_country:
            triggered_signals.append("NEW_COUNTRY_DETECTED")

        # 5. Diurnal activity
        unusual_hour = int(features.get("is_unusual_hour", 0))
        sd = 0.5 * unusual_hour
        if unusual_hour:
            triggered_signals.append("OFF_HOURS_ACTIVITY")

        # Composite weighted synthesis
        score = (
            (0.35 * sz) +
            (0.25 * sv) +
            (0.20 * sk) +
            (0.15 * sn) +
            (0.05 * sd)
        )
        bounded_score = round(min(1.0, max(0.0, score)), 4)
        return bounded_score, triggered_signals
