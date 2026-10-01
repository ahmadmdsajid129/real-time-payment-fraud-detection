"""Cold Start Management and Entity Resolution for Fraud Detection.

Handles new cardholder onboarding without historical velocity, applies Bayesian
shrinkage on customer baselines, and detects cross-account device sharing syndicates.
"""

from typing import Dict, Any, List, Set, Optional, Tuple
from enum import Enum


class AccountMaturity(str, Enum):
    COLD_START = "COLD_START"      # 0 transactions
    WARMING = "WARMING"            # 1 to 3 transactions
    MATURE = "MATURE"              # 4+ transactions


class ColdStartManager:
    """Manages behavioral baselines for new and warming customer accounts."""

    def __init__(
        self,
        population_avg_amount: float = 85.0,
        population_std_amount: float = 35.0,
        prior_weight_m: float = 5.0,
    ):
        self.pop_avg = population_avg_amount
        self.pop_std = population_std_amount
        self.m = prior_weight_m

    def determine_maturity(self, historical_txn_count: int) -> AccountMaturity:
        """Categorizes cardholder profile maturity based on historical event count."""
        if historical_txn_count <= 0:
            return AccountMaturity.COLD_START
        elif historical_txn_count <= 3:
            return AccountMaturity.WARMING
        return AccountMaturity.MATURE

    def compute_bayesian_shrunk_baseline(
        self,
        observed_amounts: List[float],
    ) -> Tuple[float, float]:
        """Calculates Bayesian shrinkage smoothed mean and standard deviation.
        
        Formula: mu_shrunk = (N * x_bar + M * mu_0) / (N + M)
        Prevents single extreme early transaction from skewing cardholder baseline.
        """
        n = len(observed_amounts)
        if n == 0:
            return self.pop_avg, self.pop_std

        x_bar = float(sum(observed_amounts) / n)
        # Bayesian weighted mean
        mu_shrunk = (n * x_bar + self.m * self.pop_avg) / (n + self.m)

        # Variance estimation with shrinkage
        if n > 1:
            sample_std = float((sum((x - x_bar) ** 2 for x in observed_amounts) / (n - 1)) ** 0.5)
            std_shrunk = max(10.0, (n * sample_std + self.m * self.pop_std) / (n + self.m))
        else:
            std_shrunk = self.pop_std

        return round(mu_shrunk, 2), round(std_shrunk, 2)


class EntityResolver:
    """Detects multi-accounting syndicates and device collision clusters."""

    def __init__(self, syndicate_threshold_custs: int = 3):
        self.syndicate_threshold = syndicate_threshold_custs

    def evaluate_device_syndicate(
        self,
        device_id: str,
        current_customer_id: str,
        device_txns_last_24h: List[Dict[str, Any]],
    ) -> Tuple[bool, int, float]:
        """Detects if a device is being shared across multiple unrelated cardholders.
        
        Returns:
            (is_syndicate: bool, distinct_customers_count: int, syndicate_risk_boost: float)
        """
        seen_customers: Set[str] = set()
        for t in device_txns_last_24h:
            cust = t.get("customer_id")
            if cust:
                seen_customers.add(cust)
        seen_customers.add(current_customer_id)

        distinct_count = len(seen_customers)
        is_syndicate = distinct_count >= self.syndicate_threshold

        # Multi-carding risk multiplier
        if distinct_count >= 5:
            risk_boost = 0.50
        elif distinct_count >= 3:
            risk_boost = 0.30
        else:
            risk_boost = 0.0

        return is_syndicate, distinct_count, risk_boost
