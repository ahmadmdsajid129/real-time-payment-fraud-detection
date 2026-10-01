"""Financial Loss & Cost Model for Risk Decisions.

Evaluates asymmetric costs between approving fraudulent transactions (chargebacks)
and blocking legitimate cardholders (customer insult/churn).
"""

from typing import Dict, Any


class FinancialCostModel:
    """Computes expected economic losses across decision outcomes."""

    def __init__(
        self,
        chargeback_fee: float = 25.0,
        customer_insult_cost: float = 35.0,
        analyst_review_cost: float = 4.0,
        customer_friction_cost: float = 2.0,
    ):
        self.chargeback_fee = chargeback_fee
        self.customer_insult_cost = customer_insult_cost
        self.analyst_review_cost = analyst_review_cost
        self.customer_friction_cost = customer_friction_cost

    def compute_expected_costs(self, amount: float, calibrated_prob: float) -> Dict[str, float]:
        """Calculates expected losses for all possible decision branches.
        
        Args:
            amount: Transaction amount in currency units
            calibrated_prob: Calibrated likelihood that transaction is fraudulent [0.0, 1.0]
        """
        p = max(0.0, min(1.0, float(calibrated_prob)))
        amt = max(0.0, float(amount))

        # Expected cost if approved (risk of false negative)
        # If fraud, lose full transaction amount + chargeback fee
        expected_approve_cost = p * (amt + self.chargeback_fee)

        # Expected cost if blocked (risk of false positive)
        # If legitimate, customer insult and churn probability
        expected_block_cost = (1.0 - p) * self.customer_insult_cost

        # Expected cost if reviewed
        # Cost of human analyst investigation + mild friction
        expected_review_cost = self.analyst_review_cost + ((1.0 - p) * self.customer_friction_cost)

        return {
            "expected_cost_approve": round(expected_approve_cost, 2),
            "expected_cost_review": round(expected_review_cost, 2),
            "expected_cost_block": round(expected_block_cost, 2),
        }
