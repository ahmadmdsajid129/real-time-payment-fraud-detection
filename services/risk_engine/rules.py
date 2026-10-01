"""Deterministic Rule Engine for the Payment Risk Decision Platform.

Evaluates domain-specific heuristic security and risk triggers.
Rules emit normalized penalties in [0.0, 1.0] and forensic explanation codes.
"""

from typing import Dict, Any, List, Tuple
from pydantic import BaseModel, Field


class TriggeredRule(BaseModel):
    """Encapsulates a fired deterministic business rule."""
    rule_code: str
    description: str
    severity_penalty: float = Field(..., ge=0.0, le=1.0)
    category: str


class RuleEngine:
    """Evaluates configurable business rules on transaction feature payloads."""

    RULE_DEFINITIONS = {
        "R01_IMPOSSIBLE_TRAVEL": {
            "description": "Geographic transit speed exceeds commercial flight physics (>900 km/h over >200 km)",
            "severity": 0.90,
            "category": "KINEMATICS",
        },
        "R02_VELOCITY_BURST_1M": {
            "description": "Transaction velocity spike (>=3 transactions within 60 seconds)",
            "severity": 0.80,
            "category": "VELOCITY",
        },
        "R03_NEW_DEVICE_HIGH_AMOUNT": {
            "description": "Account Takeover pattern: Unrecognized device combined with high spending z-score (>3.0)",
            "severity": 0.75,
            "category": "ACCOUNT_TAKEOVER",
        },
        "R04_NEW_COUNTRY_FIRST_TIME": {
            "description": "First-time international transaction exceeding INR 5,000",
            "severity": 0.60,
            "category": "GEOGRAPHY",
        },
        "R05_DEVICE_SHARING_ANOMALY": {
            "description": "Syndicate pattern: Device observed across >=4 distinct customer accounts in 24h",
            "severity": 0.85,
            "category": "DEVICE_SYNDICATE",
        },
        "R06_UNUSUAL_HOUR_LARGE_SPEND": {
            "description": "Off-hours transaction with amount exceeding 5x customer historical average",
            "severity": 0.50,
            "category": "DIURNAL",
        },
        "R07_HIGH_AMOUNT_ZSCORE": {
            "description": "Extreme monetary outlier exceeding 5 standard deviations from historical baseline",
            "severity": 0.70,
            "category": "MONETARY",
        },
        "R08_HIGH_RISK_MERCHANT_ANOMALY": {
            "description": "Substantial spend at high-risk merchant category (Crypto, Luxury, Gaming)",
            "severity": 0.65,
            "category": "MERCHANT",
        },
    }

    def evaluate(self, features: Dict[str, Any]) -> Tuple[float, List[TriggeredRule]]:
        """Evaluates all rules on the feature dictionary.
        
        Returns:
            (normalized_rule_score: float in [0.0, 1.0], triggered_rules: List[TriggeredRule])
        """
        triggered: List[TriggeredRule] = []

        # R01: Impossible Travel
        if int(features.get("impossible_travel", 0)) == 1 or (
            float(features.get("travel_speed_kmh", 0.0)) > 900.0 and float(features.get("geo_distance_km", 0.0)) > 200.0
        ):
            def_r01 = self.RULE_DEFINITIONS["R01_IMPOSSIBLE_TRAVEL"]
            triggered.append(TriggeredRule(
                rule_code="R01_IMPOSSIBLE_TRAVEL",
                description=def_r01["description"],
                severity_penalty=def_r01["severity"],
                category=def_r01["category"],
            ))

        # R02: Velocity Burst 1M
        if int(features.get("txn_count_1m", 0)) >= 3:
            def_r02 = self.RULE_DEFINITIONS["R02_VELOCITY_BURST_1M"]
            triggered.append(TriggeredRule(
                rule_code="R02_VELOCITY_BURST_1M",
                description=def_r02["description"],
                severity_penalty=def_r02["severity"],
                category=def_r02["category"],
            ))

        # R03: New Device + High Amount
        if int(features.get("is_new_device", 0)) == 1 and float(features.get("customer_amount_zscore", 0.0)) > 3.0:
            def_r03 = self.RULE_DEFINITIONS["R03_NEW_DEVICE_HIGH_AMOUNT"]
            triggered.append(TriggeredRule(
                rule_code="R03_NEW_DEVICE_HIGH_AMOUNT",
                description=def_r03["description"],
                severity_penalty=def_r03["severity"],
                category=def_r03["category"],
            ))

        # R04: New Country First Time Large Amount
        if int(features.get("is_new_country", 0)) == 1 and float(features.get("amount", 0.0)) > 5000.0:
            def_r04 = self.RULE_DEFINITIONS["R04_NEW_COUNTRY_FIRST_TIME"]
            triggered.append(TriggeredRule(
                rule_code="R04_NEW_COUNTRY_FIRST_TIME",
                description=def_r04["description"],
                severity_penalty=def_r04["severity"],
                category=def_r04["category"],
            ))

        # R05: Device Sharing Anomaly
        if int(features.get("device_customer_count", 1)) >= 4:
            def_r05 = self.RULE_DEFINITIONS["R05_DEVICE_SHARING_ANOMALY"]
            triggered.append(TriggeredRule(
                rule_code="R05_DEVICE_SHARING_ANOMALY",
                description=def_r05["description"],
                severity_penalty=def_r05["severity"],
                category=def_r05["category"],
            ))

        # R06: Unusual Hour + Large Spend
        if int(features.get("is_unusual_hour", 0)) == 1 and float(features.get("amount_to_avg_ratio", 1.0)) > 5.0:
            def_r06 = self.RULE_DEFINITIONS["R06_UNUSUAL_HOUR_LARGE_SPEND"]
            triggered.append(TriggeredRule(
                rule_code="R06_UNUSUAL_HOUR_LARGE_SPEND",
                description=def_r06["description"],
                severity_penalty=def_r06["severity"],
                category=def_r06["category"],
            ))

        # R07: Extreme Amount Z-score
        if float(features.get("customer_amount_zscore", 0.0)) >= 5.0:
            def_r07 = self.RULE_DEFINITIONS["R07_HIGH_AMOUNT_ZSCORE"]
            triggered.append(TriggeredRule(
                rule_code="R07_HIGH_AMOUNT_ZSCORE",
                description=def_r07["description"],
                severity_penalty=def_r07["severity"],
                category=def_r07["category"],
            ))

        # R08: Merchant Category Anomaly
        if float(features.get("merchant_risk_score", 0.0)) >= 0.70 and float(features.get("amount_to_avg_ratio", 1.0)) > 4.0:
            def_r08 = self.RULE_DEFINITIONS["R08_HIGH_RISK_MERCHANT_ANOMALY"]
            triggered.append(TriggeredRule(
                rule_code="R08_HIGH_RISK_MERCHANT_ANOMALY",
                description=def_r08["description"],
                severity_penalty=def_r08["severity"],
                category=def_r08["category"],
            ))

        # Sum penalties bounded at 1.0
        total_penalty = sum(r.severity_penalty for r in triggered)
        rule_score = round(min(1.0, total_penalty), 4)

        return rule_score, triggered
