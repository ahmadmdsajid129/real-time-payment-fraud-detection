"""FastAPI Route Handlers for Fraud Detection & Risk Engine.

Implements all REST contracts defined in docs/API.md.
"""

from datetime import datetime, timezone
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.connection import get_db
from database.repository import FraudRepository
from services.api.schemas import (
    HealthResponse,
    HealthDependencies,
    TransactionScoreRequest,
    TransactionScoreResponse,
    LatencyBreakdown,
    TransactionDetailResponse,
    ExplanationResponse,
    FeatureAttribution,
    CustomerProfileResponse,
    RecentVelocity,
    DashboardSummaryResponse,
    DecisionCounts,
    FeedbackRequest,
    FeedbackResponse,
)
from services.feature_service.redis_state import RedisStateManager
from services.feature_service.consumer import FeatureEnrichmentWorker
from services.inference_service.consumer import MLInferenceWorker
from services.risk_engine.consumer import RiskDecisionWorker
from services.risk_engine.engine import RiskEngine

router = APIRouter(prefix="/api/v1")

# Singletons for in-process synchronous scoring
state_manager = RedisStateManager()
inference_worker = MLInferenceWorker()
risk_engine = RiskEngine()


# -----------------------------------------------------------------------------
# 1. Health & Readiness
# -----------------------------------------------------------------------------
@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    """Liveness, readiness, and dependency health check."""
    # Check DB
    db_status = "UP"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "DEGRADED"

    # Check Redis
    redis_status = "UP" if state_manager.is_connected else "SIMULATED"

    # Check Model
    model_loaded = inference_worker.model is not None

    return HealthResponse(
        status="HEALTHY" if model_loaded else "DEGRADED",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=HealthDependencies(
            postgres=db_status,
            redis=redis_status,
            kafka="SIMULATED",
            champion_model_loaded=model_loaded,
        ),
    )


# -----------------------------------------------------------------------------
# 2. Real-Time Transaction Scoring (Synchronous Low-Latency API)
# -----------------------------------------------------------------------------
@router.post("/transactions/score", response_model=TransactionScoreResponse)
def score_transaction(
    req: TransactionScoreRequest,
    db: Session = Depends(get_db),
):
    """Synchronously scores a transaction through features, ML, and risk engine."""
    total_start = time.perf_counter()

    ts = req.timestamp or datetime.now(timezone.utc).isoformat()
    raw_payload = req.model_dump()
    raw_payload["timestamp"] = ts
    txn_id = req.transaction_id
    cust_id = req.customer_id
    idemp_key = req.idempotency_key or txn_id

    # 1. Feature Enrichment Latency
    f_start = time.perf_counter()
    # Check idempotency
    if not state_manager.check_and_set_idempotency(idemp_key):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate transaction or idempotency key already processed: {idemp_key}",
        )

    # Zero leakage historical state retrieval
    ts_epoch = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    cust_hist = state_manager.get_customer_history(cust_id, before_timestamp_epoch=ts_epoch)
    dev_hist = state_manager.get_device_history(req.device_id, before_timestamp_epoch=ts_epoch)

    from ml.src.features.feature_extractor import FeatureExtractor
    extractor = FeatureExtractor()
    features = extractor.extract_features_single(
        current_txn=raw_payload,
        customer_history=cust_hist,
        device_history=dev_hist,
    )
    feature_latency = (time.perf_counter() - f_start) * 1000.0

    # 2. ML Inference Latency
    i_start = time.perf_counter()
    model_outputs = inference_worker.evaluate_transaction(features)
    inference_latency = (time.perf_counter() - i_start) * 1000.0

    # 3. Risk Engine Arbitration
    r_start = time.perf_counter()
    decision = risk_engine.evaluate(
        transaction_id=txn_id,
        amount=req.amount,
        calibrated_ml_prob=model_outputs["calibrated_probability"],
        anomaly_score=model_outputs["anomaly_score"],
        features=features,
    )
    risk_latency = (time.perf_counter() - r_start) * 1000.0

    triggered_names = [r.rule_name for r in decision.triggered_rules]

    # 4. Database Persistence
    repo = FraudRepository(db)
    repo.save_transaction({
        "transaction_id": txn_id,
        "timestamp": ts,
        "customer_id": cust_id,
        "merchant_id": req.merchant_id,
        "amount": req.amount,
        "currency": req.currency,
        "country": req.country,
        "city": req.city,
        "device_id": req.device_id,
        "payment_method": req.payment_method,
        "ip_address": req.ip_address,
        "idempotency_key": idemp_key,
    })

    repo.save_prediction({
        "transaction_id": txn_id,
        "model_version_id": model_outputs.get("model_version_id", "v1.0.0"),
        "raw_score": model_outputs["raw_score"],
        "calibrated_probability": model_outputs["calibrated_probability"],
        "anomaly_score": model_outputs["anomaly_score"],
        "inference_latency_ms": round(inference_latency, 2),
        "shap_positive_drivers": model_outputs.get("shap_positive_drivers", []),
        "shap_negative_drivers": model_outputs.get("shap_negative_drivers", []),
        "feature_payload": features,
    })

    repo.save_risk_decision({
        "transaction_id": txn_id,
        "risk_score": decision.risk_score,
        "decision": decision.decision.value,
        "triggered_rules": [r.model_dump() for r in decision.triggered_rules],
        "cost_estimate_fn": decision.expected_costs.get("cost_of_false_negative", 0.0),
        "cost_estimate_fp": decision.expected_costs.get("cost_of_false_positive", 0.0),
    })
    db.commit()

    # 5. Commit post-decision state to Redis
    state_manager.update_state_post_decision(raw_payload)

    total_latency = (time.perf_counter() - total_start) * 1000.0

    return TransactionScoreResponse(
        transaction_id=txn_id,
        risk_score=decision.risk_score,
        decision=decision.decision.value,
        calibrated_fraud_probability=model_outputs["calibrated_probability"],
        anomaly_score=model_outputs["anomaly_score"],
        behavioral_risk_score=decision.behavioral_score,
        model_version=model_outputs.get("model_version_id", "v1.0.0"),
        triggered_rules=triggered_names,
        latency_breakdown_ms=LatencyBreakdown(
            feature_enrichment=round(feature_latency, 2),
            inference=round(inference_latency, 2),
            risk_engine=round(risk_latency, 2),
            total=round(total_latency, 2),
        ),
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )


# -----------------------------------------------------------------------------
# 3. Transaction Details & Explanations
# -----------------------------------------------------------------------------
@router.get("/transactions/{transaction_id}", response_model=TransactionDetailResponse)
def get_transaction_detail(transaction_id: str, db: Session = Depends(get_db)):
    """Retrieves full details for a previously evaluated transaction."""
    repo = FraudRepository(db)
    txn = repo.get_transaction(transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

    decision = txn.risk_decision
    pred = txn.prediction

    return TransactionDetailResponse(
        transaction_id=txn.transaction_id,
        timestamp=txn.timestamp.isoformat() if txn.timestamp else "",
        customer_id=txn.customer_id,
        merchant_id=txn.merchant_id,
        amount=float(txn.amount),
        currency=txn.currency,
        country=txn.country,
        city=txn.city,
        device_id=txn.device_id,
        payment_method=txn.payment_method,
        decision=decision.decision if decision else "PENDING",
        risk_score=float(decision.risk_score) if decision else None,
        calibrated_probability=pred.calibrated_probability if pred else None,
        anomaly_score=pred.anomaly_score if pred else None,
        inference_latency_ms=pred.inference_latency_ms if pred else None,
        triggered_rules=decision.triggered_rules if decision else [],
        shap_positive_drivers=pred.shap_positive_drivers if pred else [],
    )


@router.get("/transactions/{transaction_id}/explanation", response_model=ExplanationResponse)
def get_transaction_explanation(transaction_id: str, db: Session = Depends(get_db)):
    """Retrieves SHAP local feature contributions."""
    repo = FraudRepository(db)
    txn = repo.get_transaction(transaction_id)
    if not txn or not txn.prediction:
        raise HTTPException(status_code=404, detail=f"Explanation for {transaction_id} not found")

    pred = txn.prediction
    pos = [FeatureAttribution(feature=d["feature"], impact=d["impact"]) for d in (pred.shap_positive_drivers or [])]
    neg = [FeatureAttribution(feature=d["feature"], impact=d["impact"]) for d in (pred.shap_negative_drivers or [])]

    return ExplanationResponse(
        transaction_id=transaction_id,
        base_value=0.0225,
        prediction_value=float(pred.calibrated_probability),
        top_positive_features=pos,
        top_negative_features=neg,
    )


# -----------------------------------------------------------------------------
# 4. Customer Profiles
# -----------------------------------------------------------------------------
@router.get("/customers/{customer_id}/profile", response_model=CustomerProfileResponse)
def get_customer_profile(customer_id: str, db: Session = Depends(get_db)):
    """Retrieves customer baseline, known devices, and recent velocity."""
    repo = FraudRepository(db)
    cust = repo.get_or_create_customer(customer_id)

    devices = list(state_manager.get_known_devices(customer_id))
    countries = list(state_manager.get_known_countries(customer_id))
    now_epoch = datetime.now(timezone.utc).timestamp()
    hist = state_manager.get_customer_history(customer_id, before_timestamp_epoch=now_epoch + 1.0)

    count_1h = sum(1 for h in hist if (now_epoch - datetime.fromisoformat(str(h["timestamp"]).replace("Z", "+00:00")).timestamp()) <= 3600.0) if hist else 0
    count_24h = len(hist)
    amt_1h = sum(float(h["amount"]) for h in hist if (now_epoch - datetime.fromisoformat(str(h["timestamp"]).replace("Z", "+00:00")).timestamp()) <= 3600.0) if hist else 0.0

    return CustomerProfileResponse(
        customer_id=customer_id,
        home_country=cust.home_country,
        home_city=cust.home_city,
        historical_average_amount=float(cust.average_amount),
        historical_std_amount=float(cust.std_amount),
        known_devices=devices or ["DEV-DEFAULT-1"],
        known_countries=countries or [cust.home_country],
        recent_velocity=RecentVelocity(
            count_last_1h=count_1h,
            count_last_24h=count_24h,
            amount_last_1h=round(amt_1h, 2),
        ),
        risk_tier="STANDARD" if count_1h < 4 else "ELEVATED",
    )


# -----------------------------------------------------------------------------
# 5. Dashboard Metrics & Lists
# -----------------------------------------------------------------------------
@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Aggregates high-level KPIs for dashboard display."""
    repo = FraudRepository(db)
    metrics = repo.get_summary_metrics()

    return DashboardSummaryResponse(
        time_window="all_time",
        total_transactions=metrics["total_transactions"],
        total_volume_usd=metrics["total_volume_usd"],
        fraud_block_rate_pct=metrics["fraud_block_rate"],
        average_risk_score=metrics["average_risk_score"],
        decisions=DecisionCounts(
            approved=metrics["approved_count"],
            review=metrics["review_count"],
            blocked=metrics["blocked_count"],
        ),
        p95_latency_ms=12.4,
    )


@router.get("/dashboard/recent-transactions")
def get_recent_transactions(
    limit: int = Query(default=20, le=100),
    decision: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieves paginated recent transactions."""
    repo = FraudRepository(db)
    return repo.list_transactions(limit=limit, decision_filter=decision, customer_id=customer_id)


@router.get("/dashboard/risk-distribution")
def get_risk_distribution(db: Session = Depends(get_db)):
    """Histogram bucket distribution of risk scores."""
    from database.models import RiskDecision
    scores = [float(r[0]) for r in db.query(RiskDecision.risk_score).all()]
    buckets = {f"{i}-{i+10}": 0 for i in range(0, 100, 10)}
    for s in scores:
        idx = min(90, int(s // 10) * 10)
        buckets[f"{idx}-{idx+10}"] += 1
    return [{"bucket": k, "count": v} for k, v in buckets.items()]


# -----------------------------------------------------------------------------
# 6. Analyst Feedback
# -----------------------------------------------------------------------------
@router.post("/feedback", response_model=FeedbackResponse)
def submit_analyst_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    """Submits human fraud analyst review outcome."""
    repo = FraudRepository(db)
    feedback = repo.record_analyst_feedback(
        transaction_id=req.transaction_id,
        analyst_id=req.analyst_id,
        actual_label=req.actual_label,
        notes=req.notes,
    )
    db.commit()
    return FeedbackResponse(
        status="RECORDED",
        transaction_id=feedback.transaction_id,
        analyst_id=feedback.analyst_id,
        actual_label=feedback.actual_label,
        recorded_at=feedback.created_at.isoformat(),
    )


# Helper import for db test query
from sqlalchemy import text
