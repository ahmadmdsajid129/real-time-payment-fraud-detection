"""SQLAlchemy ORM Data Models for Fraud Detection & Risk Engine.

Mirrors relational database schema defined in database/schema.sql.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Numeric,
    Float,
    Integer,
    SmallInteger,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship
from database.connection import Base


def utc_now():
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(64), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    home_country = Column(String(2), nullable=False)
    home_city = Column(String(64), nullable=False)
    average_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    std_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    typical_hour_start = Column(SmallInteger, default=8, nullable=False)
    typical_hour_end = Column(SmallInteger, default=22, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)

    transactions = relationship("Transaction", back_populates="customer")


class Merchant(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False)
    mcc_code = Column(String(4), nullable=False)
    country = Column(String(2), nullable=False)
    city = Column(String(64), nullable=False)
    risk_tier = Column(String(16), default="STANDARD", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    transactions = relationship("Transaction", back_populates="merchant")


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(64), primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    customer_id = Column(String(64), ForeignKey("customers.customer_id"), nullable=False, index=True)
    merchant_id = Column(String(64), ForeignKey("merchants.merchant_id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    country = Column(String(2), nullable=False)
    city = Column(String(64), nullable=False)
    device_id = Column(String(64), nullable=False, index=True)
    payment_method = Column(String(32), nullable=False)
    ip_address = Column(String(45), nullable=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    customer = relationship("Customer", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    prediction = relationship("Prediction", back_populates="transaction", uselist=False)
    risk_decision = relationship("RiskDecision", back_populates="transaction", uselist=False)
    feedback_entries = relationship("Feedback", back_populates="transaction")
    fraud_label = relationship("FraudLabel", back_populates="transaction", uselist=False)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    version_id = Column(String(64), primary_key=True)
    model_name = Column(String(64), nullable=False)
    algorithm = Column(String(64), nullable=False)
    is_champion = Column(Boolean, default=False, nullable=False)
    pr_auc = Column(Float, nullable=False)
    roc_auc = Column(Float, nullable=False)
    brier_score = Column(Float, nullable=False)
    parameters = Column(JSON, nullable=False)
    trained_at = Column(DateTime(timezone=True), nullable=False)
    deployed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    predictions = relationship("Prediction", back_populates="model_version")


class Prediction(Base):
    __tablename__ = "predictions"

    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), ForeignKey("transactions.transaction_id", ondelete="CASCADE"), unique=True, nullable=False)
    model_version_id = Column(String(64), ForeignKey("model_versions.version_id"), nullable=False)
    raw_score = Column(Float, nullable=False)
    calibrated_probability = Column(Float, nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False)
    inference_latency_ms = Column(Float, nullable=False)
    shap_positive_drivers = Column(JSON, nullable=False, default=list)
    shap_negative_drivers = Column(JSON, nullable=False, default=list)
    feature_payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    transaction = relationship("Transaction", back_populates="prediction")
    model_version = relationship("ModelVersion", back_populates="predictions")


class RiskDecision(Base):
    __tablename__ = "risk_decisions"

    decision_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), ForeignKey("transactions.transaction_id", ondelete="CASCADE"), unique=True, nullable=False)
    risk_score = Column(Numeric(5, 2), nullable=False, index=True)
    decision = Column(String(16), nullable=False, index=True)
    triggered_rules = Column(JSON, nullable=False, default=list)
    cost_estimate_fn = Column(Numeric(10, 2), nullable=True)
    cost_estimate_fp = Column(Numeric(10, 2), nullable=True)
    status = Column(String(20), default="FINAL", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    transaction = relationship("Transaction", back_populates="risk_decision")


class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), ForeignKey("transactions.transaction_id", ondelete="CASCADE"), nullable=False, index=True)
    analyst_id = Column(String(64), nullable=False)
    actual_label = Column(String(16), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    transaction = relationship("Transaction", back_populates="feedback_entries")


class FraudLabel(Base):
    __tablename__ = "fraud_labels"

    transaction_id = Column(String(64), ForeignKey("transactions.transaction_id", ondelete="CASCADE"), primary_key=True)
    is_fraud = Column(Boolean, nullable=False, index=True)
    label_source = Column(String(32), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    transaction = relationship("Transaction", back_populates="fraud_label")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    target_resource = Column(String(128), nullable=False)
    details = Column(JSON, nullable=False, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
