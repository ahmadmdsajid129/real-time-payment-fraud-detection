"""Risk Arbitration Engine & Decision Policy.

Synthesizes multiple normalized risk signals (Calibrated ML, Anomaly, Behavioral, Rules)
into a bounded 0-100 composite risk score and outputs APPROVE / REVIEW / BLOCK.
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from services.risk_engine.rules import RuleEngine, TriggeredRule
from services.risk_engine.cost_model import FinancialCostModel
from ml.src.features.behavioral_profiler import BehavioralProfiler


class DecisionEnum(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class RiskDecision(BaseModel):
    """Complete arbitrated transaction risk evaluation."""
    transaction_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Composite score between 0.0 and 100.0")
    decision: DecisionEnum
    calibrated_probability: float = Field(..., ge=0.0, le=1.0)
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    behavioral_score: float = Field(..., ge=0.0, le=1.0)
    rule_score: float = Field(..., ge=0.0, le=1.0)
    triggered_rules: List[TriggeredRule]
    behavioral_signals: List[str]
    expected_costs: Dict[str, float]


class RiskEngine:
    """Configurable risk arbitration engine mapping multi-factor signals to decisions."""

    def __init__(
        self,
        weight_ml: float = 0.55,
        weight_anomaly: float = 0.15,
        weight_behavioral: float = 0.15,
        weight_rules: float = 0.15,
        approve_threshold: float = 30.0,
        block_threshold: float = 75.0,
    ):
        weights_sum = weight_ml + weight_anomaly + weight_behavioral + weight_rules
        assert abs(weights_sum - 1.0) < 1e-4, f"Risk weights must sum to 1.0, got {weights_sum}"
        self.w_ml = weight_ml
        self.w_anom = weight_anomaly
        self.w_behav = weight_behavioral
        self.w_rules = weight_rules
        self.thresh_approve = approve_threshold
        self.thresh_block = block_threshold

        self.rule_engine = RuleEngine()
        self.cost_model = FinancialCostModel()

    def evaluate(
        self,
        transaction_id: str,
        amount: float,
        calibrated_ml_prob: float,
        anomaly_score: float,
        features: Dict[str, Any],
    ) -> RiskDecision:
        """Evaluates an enriched transaction and emits an arbitrated RiskDecision."""
        # 1. Clamp inputs to safe [0.0, 1.0] domain
        p_ml = min(1.0, max(0.0, float(calibrated_ml_prob)))
        s_anom = min(1.0, max(0.0, float(anomaly_score)))

        # 2. Behavioral Volatility Scoring
        s_behav, b_signals = BehavioralProfiler.score_behavior(features)

        # 3. Deterministic Rules Evaluation
        s_rules, triggered_rules = self.rule_engine.evaluate(features)

        # 4. Composite Risk Score (0 - 100)
        composite = (
            (self.w_ml * p_ml) +
            (self.w_anom * s_anom) +
            (self.w_behav * s_behav) +
            (self.w_rules * s_rules)
        )
        score_100 = round(min(100.0, max(0.0, composite * 100.0)), 2)

        # 5. Triage Decision Policy
        if score_100 < self.thresh_approve:
            decision = DecisionEnum.APPROVE
        elif score_100 < self.thresh_block:
            decision = DecisionEnum.REVIEW
        else:
            decision = DecisionEnum.BLOCK

        # 6. Cost Model Estimates
        expected_costs = self.cost_model.compute_expected_costs(amount=amount, calibrated_prob=p_ml)

        return RiskDecision(
            transaction_id=transaction_id,
            risk_score=score_100,
            decision=decision,
            calibrated_probability=round(p_ml, 4),
            anomaly_score=round(s_anom, 4),
            behavioral_score=round(s_behav, 4),
            rule_score=round(s_rules, 4),
            triggered_rules=triggered_rules,
            behavioral_signals=b_signals,
            expected_costs=expected_costs,
        )
