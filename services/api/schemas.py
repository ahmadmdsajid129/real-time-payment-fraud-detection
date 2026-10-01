"""Pydantic Request and Response Schemas for the FastAPI REST API.

Enforces strict typed interfaces according to docs/API.md specifications.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Health & Status
# -----------------------------------------------------------------------------
class HealthDependencies(BaseModel):
    postgres: str = "UP"
    redis: str = "UP"
    kafka: str = "UP"
    champion_model_loaded: bool = True


class HealthResponse(BaseModel):
    status: str = "HEALTHY"
    version: str = "1.0.0"
    timestamp: str
    dependencies: HealthDependencies


# -----------------------------------------------------------------------------
# Transactions & Scoring
# -----------------------------------------------------------------------------
class TransactionScoreRequest(BaseModel):
    transaction_id: str = Field(..., example="TXN-8839210")
    timestamp: Optional[str] = Field(default=None, example="2026-10-01T12:15:30Z")
    customer_id: str = Field(..., example="CUST-10492")
    merchant_id: str = Field(default="MERCH-4091", example="MERCH-4091")
    amount: float = Field(..., gt=0.0, example=450.00)
    currency: str = Field(default="USD", example="USD")
    country: str = Field(default="US", example="US")
    city: str = Field(default="New York", example="New York")
    lat: Optional[float] = Field(default=40.7128)
    lon: Optional[float] = Field(default=-74.0060)
    device_id: str = Field(default="DEV-MOBILE-01", example="DEV-MOBILE-01")
    payment_method: str = Field(default="credit_card", example="credit_card")
    ip_address: Optional[str] = Field(default="192.168.1.1", example="192.168.1.1")
    idempotency_key: Optional[str] = None


class LatencyBreakdown(BaseModel):
    feature_enrichment: float
    inference: float
    risk_engine: float
    total: float


class TransactionScoreResponse(BaseModel):
    transaction_id: str
    risk_score: float
    decision: str
    calibrated_fraud_probability: float
    anomaly_score: float
    behavioral_risk_score: float
    model_version: str
    triggered_rules: List[str]
    latency_breakdown_ms: LatencyBreakdown
    evaluated_at: str


class TransactionDetailResponse(BaseModel):
    transaction_id: str
    timestamp: str
    customer_id: str
    merchant_id: str
    amount: float
    currency: str
    country: str
    city: str
    device_id: str
    payment_method: str
    decision: str
    risk_score: Optional[float] = None
    calibrated_probability: Optional[float] = None
    anomaly_score: Optional[float] = None
    inference_latency_ms: Optional[float] = None
    triggered_rules: List[Dict[str, Any]] = []
    shap_positive_drivers: List[Dict[str, Any]] = []


# -----------------------------------------------------------------------------
# Explanations (SHAP)
# -----------------------------------------------------------------------------
class FeatureAttribution(BaseModel):
    feature: str
    impact: float


class ExplanationResponse(BaseModel):
    transaction_id: str
    base_value: float = 0.02
    prediction_value: float
    top_positive_features: List[FeatureAttribution]
    top_negative_features: List[FeatureAttribution]


# -----------------------------------------------------------------------------
# Customer Profiles
# -----------------------------------------------------------------------------
class RecentVelocity(BaseModel):
    count_last_1h: int
    count_last_24h: int
    amount_last_1h: float


class CustomerProfileResponse(BaseModel):
    customer_id: str
    home_country: str
    home_city: str
    historical_average_amount: float
    historical_std_amount: float
    known_devices: List[str]
    known_countries: List[str]
    recent_velocity: RecentVelocity
    risk_tier: str = "STANDARD"


# -----------------------------------------------------------------------------
# Dashboard & KPIs
# -----------------------------------------------------------------------------
class DecisionCounts(BaseModel):
    approved: int
    review: int
    blocked: int


class DashboardSummaryResponse(BaseModel):
    time_window: str = "all_time"
    total_transactions: int
    total_volume_usd: float
    fraud_block_rate_pct: float
    average_risk_score: float
    decisions: DecisionCounts
    p95_latency_ms: float = 14.5


class FeedbackRequest(BaseModel):
    transaction_id: str
    analyst_id: str
    actual_label: str = Field(..., regex="^(FRAUD|LEGITIMATE)$")
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str
    transaction_id: str
    analyst_id: str
    actual_label: str
    recorded_at: str
