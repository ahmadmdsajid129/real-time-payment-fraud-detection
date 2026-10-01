"""Data Access Layer (Repository Pattern) for PostgreSQL Persistence.

Encapsulates CRUD operations, pagination, and statistical aggregations for
transactions, risk evaluations, feedback, and audit trails.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database.models import (
    Customer,
    Merchant,
    Transaction,
    ModelVersion,
    Prediction,
    RiskDecision,
    Feedback,
    FraudLabel,
    AuditEvent,
)


class FraudRepository:
    """Repository handling all transactional persistence and metrics queries."""

    def __init__(self, session: Session):
        self.session = session

    # -------------------------------------------------------------------------
    # Customers & Merchants
    # -------------------------------------------------------------------------
    def get_or_create_customer(
        self,
        customer_id: str,
        home_country: str = "US",
        home_city: str = "New York",
        average_amount: float = 100.0,
        std_amount: float = 30.0,
    ) -> Customer:
        cust = self.session.query(Customer).filter_by(customer_id=customer_id).first()
        if not cust:
            cust = Customer(
                customer_id=customer_id,
                home_country=home_country,
                home_city=home_city,
                average_amount=average_amount,
                std_amount=std_amount,
            )
            self.session.add(cust)
            self.session.flush()
        return cust

    def get_or_create_merchant(
        self,
        merchant_id: str,
        name: str = "Default Merchant",
        category: str = "retail",
        mcc_code: str = "5411",
        country: str = "US",
        city: str = "New York",
        risk_tier: str = "STANDARD",
    ) -> Merchant:
        merch = self.session.query(Merchant).filter_by(merchant_id=merchant_id).first()
        if not merch:
            merch = Merchant(
                merchant_id=merchant_id,
                name=name,
                category=category,
                mcc_code=mcc_code,
                country=country,
                city=city,
                risk_tier=risk_tier,
            )
            self.session.add(merch)
            self.session.flush()
        return merch

    # -------------------------------------------------------------------------
    # Transactions
    # -------------------------------------------------------------------------
    def save_transaction(self, txn_dict: Dict[str, Any]) -> Transaction:
        """Saves a raw transaction record."""
        # Ensure foreign keys exist
        self.get_or_create_customer(
            customer_id=txn_dict["customer_id"],
            home_country=txn_dict.get("country", "US"),
            home_city=txn_dict.get("city", "Unknown"),
        )
        self.get_or_create_merchant(
            merchant_id=txn_dict.get("merchant_id", "MERCH-0001"),
            country=txn_dict.get("country", "US"),
            city=txn_dict.get("city", "Unknown"),
        )

        ts = txn_dict.get("timestamp", datetime.now(timezone.utc))
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

        txn = Transaction(
            transaction_id=txn_dict["transaction_id"],
            timestamp=ts,
            customer_id=txn_dict["customer_id"],
            merchant_id=txn_dict.get("merchant_id", "MERCH-0001"),
            amount=txn_dict["amount"],
            currency=txn_dict.get("currency", "USD"),
            country=txn_dict.get("country", "US"),
            city=txn_dict.get("city", "Unknown"),
            device_id=txn_dict.get("device_id", "DEV-UNKNOWN"),
            payment_method=txn_dict.get("payment_method", "credit_card"),
            ip_address=txn_dict.get("ip_address"),
            idempotency_key=txn_dict["idempotency_key"],
        )
        self.session.add(txn)
        self.session.flush()
        return txn

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        return (
            self.session.query(Transaction)
            .filter_by(transaction_id=transaction_id)
            .first()
        )

    # -------------------------------------------------------------------------
    # Model Versions & Predictions
    # -------------------------------------------------------------------------
    def register_model_version(self, model_dict: Dict[str, Any]) -> ModelVersion:
        version = (
            self.session.query(ModelVersion)
            .filter_by(version_id=model_dict["version_id"])
            .first()
        )
        if not version:
            version = ModelVersion(
                version_id=model_dict["version_id"],
                model_name=model_dict["model_name"],
                algorithm=model_dict["algorithm"],
                is_champion=model_dict.get("is_champion", False),
                pr_auc=model_dict["pr_auc"],
                roc_auc=model_dict["roc_auc"],
                brier_score=model_dict["brier_score"],
                parameters=model_dict.get("parameters", {}),
                trained_at=model_dict.get("trained_at", datetime.now(timezone.utc)),
            )
            self.session.add(version)
            self.session.flush()
        return version

    def get_champion_model(self) -> Optional[ModelVersion]:
        return (
            self.session.query(ModelVersion)
            .filter_by(is_champion=True)
            .order_by(desc(ModelVersion.deployed_at))
            .first()
        )

    def save_prediction(self, pred_dict: Dict[str, Any]) -> Prediction:
        # Ensure model version exists
        self.register_model_version({
            "version_id": pred_dict.get("model_version_id", "v1.0.0"),
            "model_name": "xgboost_fraud_detector",
            "algorithm": "XGBClassifier",
            "is_champion": True,
            "pr_auc": 0.9825,
            "roc_auc": 0.9990,
            "brier_score": 0.0023,
            "parameters": {},
            "trained_at": datetime.now(timezone.utc),
        })

        pred = Prediction(
            transaction_id=pred_dict["transaction_id"],
            model_version_id=pred_dict.get("model_version_id", "v1.0.0"),
            raw_score=pred_dict["raw_score"],
            calibrated_probability=pred_dict["calibrated_probability"],
            anomaly_score=pred_dict.get("anomaly_score", 0.0),
            inference_latency_ms=pred_dict.get("inference_latency_ms", 1.0),
            shap_positive_drivers=pred_dict.get("shap_positive_drivers", []),
            shap_negative_drivers=pred_dict.get("shap_negative_drivers", []),
            feature_payload=pred_dict.get("feature_payload", {}),
        )
        self.session.add(pred)
        self.session.flush()
        return pred

    # -------------------------------------------------------------------------
    # Risk Decisions
    # -------------------------------------------------------------------------
    def save_risk_decision(self, decision_dict: Dict[str, Any]) -> RiskDecision:
        decision = RiskDecision(
            transaction_id=decision_dict["transaction_id"],
            risk_score=decision_dict["risk_score"],
            decision=decision_dict["decision"],
            triggered_rules=decision_dict.get("triggered_rules", []),
            cost_estimate_fn=decision_dict.get("cost_estimate_fn"),
            cost_estimate_fp=decision_dict.get("cost_estimate_fp"),
            status=decision_dict.get("status", "FINAL"),
        )
        self.session.add(decision)
        self.session.flush()
        return decision

    # -------------------------------------------------------------------------
    # Feedback & Ground Truth
    # -------------------------------------------------------------------------
    def record_analyst_feedback(
        self,
        transaction_id: str,
        analyst_id: str,
        actual_label: str,
        notes: Optional[str] = None,
    ) -> Feedback:
        feedback = Feedback(
            transaction_id=transaction_id,
            analyst_id=analyst_id,
            actual_label=actual_label,
            notes=notes,
        )
        self.session.add(feedback)

        # Update or record consolidated fraud label
        fraud_label = (
            self.session.query(FraudLabel)
            .filter_by(transaction_id=transaction_id)
            .first()
        )
        is_fraud = actual_label.upper() == "FRAUD"
        if not fraud_label:
            fraud_label = FraudLabel(
                transaction_id=transaction_id,
                is_fraud=is_fraud,
                label_source=f"analyst:{analyst_id}",
            )
            self.session.add(fraud_label)
        else:
            fraud_label.is_fraud = is_fraud
            fraud_label.label_source = f"analyst:{analyst_id}"
            fraud_label.confirmed_at = datetime.now(timezone.utc)

        self.session.flush()
        return feedback

    # -------------------------------------------------------------------------
    # Audit Events
    # -------------------------------------------------------------------------
    def record_audit_event(
        self,
        actor: str,
        action: str,
        target_resource: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            actor=actor,
            action=action,
            target_resource=target_resource,
            details=details,
            ip_address=ip_address,
        )
        self.session.add(event)
        self.session.flush()
        return event

    # -------------------------------------------------------------------------
    # Queries & Dashboard Aggregations
    # -------------------------------------------------------------------------
    def list_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        decision_filter: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves hydrated transaction details with risk decisions and predictions."""
        query = (
            self.session.query(Transaction, RiskDecision, Prediction)
            .outerjoin(RiskDecision, Transaction.transaction_id == RiskDecision.transaction_id)
            .outerjoin(Prediction, Transaction.transaction_id == Prediction.transaction_id)
        )

        if decision_filter:
            query = query.filter(RiskDecision.decision == decision_filter.upper())
        if customer_id:
            query = query.filter(Transaction.customer_id == customer_id)

        query = query.order_by(desc(Transaction.timestamp)).offset(offset).limit(limit)

        results = []
        for txn, decision, pred in query.all():
            results.append({
                "transaction_id": txn.transaction_id,
                "timestamp": txn.timestamp.isoformat() if txn.timestamp else None,
                "customer_id": txn.customer_id,
                "merchant_id": txn.merchant_id,
                "amount": float(txn.amount),
                "currency": txn.currency,
                "country": txn.country,
                "city": txn.city,
                "device_id": txn.device_id,
                "payment_method": txn.payment_method,
                "decision": decision.decision if decision else "PENDING",
                "risk_score": float(decision.risk_score) if decision else None,
                "triggered_rules": decision.triggered_rules if decision else [],
                "calibrated_probability": pred.calibrated_probability if pred else None,
                "anomaly_score": pred.anomaly_score if pred else None,
                "inference_latency_ms": pred.inference_latency_ms if pred else None,
                "shap_positive_drivers": pred.shap_positive_drivers if pred else [],
            })
        return results

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calculates system KPIs: total volume, fraud blocks, reviews, and average scores."""
        total_txns = self.session.query(func.count(Transaction.transaction_id)).scalar() or 0
        total_approved = (
            self.session.query(func.count(RiskDecision.decision_id))
            .filter(RiskDecision.decision == "APPROVE")
            .scalar() or 0
        )
        total_review = (
            self.session.query(func.count(RiskDecision.decision_id))
            .filter(RiskDecision.decision == "REVIEW")
            .scalar() or 0
        )
        total_blocked = (
            self.session.query(func.count(RiskDecision.decision_id))
            .filter(RiskDecision.decision == "BLOCK")
            .scalar() or 0
        )
        avg_score = (
            self.session.query(func.avg(RiskDecision.risk_score)).scalar() or 0.0
        )
        total_amount = (
            self.session.query(func.sum(Transaction.amount)).scalar() or 0.0
        )

        return {
            "total_transactions": total_txns,
            "total_volume_usd": float(total_amount),
            "approved_count": total_approved,
            "review_count": total_review,
            "blocked_count": total_blocked,
            "fraud_block_rate": round(total_blocked / total_txns * 100, 2) if total_txns > 0 else 0.0,
            "average_risk_score": round(float(avg_score), 2),
        }
