"""Data schemas for customers, merchants, devices, and payment transactions.

Uses Pydantic V2 for strict type checking and validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class FraudScenario(str, Enum):
    """Controllable fraud scenarios for transaction generation."""
    NORMAL = "NORMAL"
    HIGH_VALUE_ANOMALY = "HIGH_VALUE_ANOMALY"
    VELOCITY_ATTACK = "VELOCITY_ATTACK"
    NEW_COUNTRY = "NEW_COUNTRY"
    NEW_DEVICE = "NEW_DEVICE"
    IMPOSSIBLE_TRAVEL = "IMPOSSIBLE_TRAVEL"
    DEVICE_SHARING = "DEVICE_SHARING"
    MERCHANT_ANOMALY = "MERCHANT_ANOMALY"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"


class PaymentMethod(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    UPI = "UPI"
    NET_BANKING = "NET_BANKING"
    WALLET = "WALLET"


class CustomerProfile(BaseModel):
    """Synthetic customer profile and historical baseline."""
    customer_id: str = Field(..., description="Unique synthetic customer identifier")
    created_at: datetime
    home_country: str = Field(..., max_length=2, min_length=2)
    home_city: str
    home_lat: float
    home_lon: float
    avg_amount: float = Field(..., ge=1.0)
    std_amount: float = Field(..., ge=0.1)
    min_amount: float = Field(..., ge=0.0)
    max_amount: float = Field(..., ge=1.0)
    preferred_merchants: List[str]
    known_devices: List[str]
    known_countries: List[str]
    typical_hour_start: int = Field(default=8, ge=0, le=23)
    typical_hour_end: int = Field(default=22, ge=0, le=23)
    avg_txns_per_week: float = Field(default=5.0, ge=0.5)


class MerchantProfile(BaseModel):
    """Synthetic merchant business profile."""
    merchant_id: str = Field(..., description="Unique merchant identifier")
    name: str
    category: str
    mcc_code: str = Field(..., max_length=4, min_length=4)
    country: str = Field(..., max_length=2, min_length=2)
    city: str
    lat: float
    lon: float
    risk_tier: str = Field(default="STANDARD")  # LOW, STANDARD, HIGH
    avg_amount: float = Field(default=1000.0, ge=1.0)


class TransactionPayload(BaseModel):
    """Single raw payment transaction payload."""
    transaction_id: str = Field(..., description="Unique transaction ID")
    timestamp: datetime = Field(..., description="UTC transaction timestamp")
    customer_id: str = Field(..., description="Foreign key to customer")
    merchant_id: str = Field(..., description="Foreign key to merchant")
    amount: float = Field(..., gt=0.0, description="Monetary transaction amount")
    currency: str = Field(default="INR", max_length=3, min_length=3)
    country: str = Field(..., max_length=2, min_length=2)
    city: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)
    device_id: str
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    ip_address: Optional[str] = None
    merchant_category: str
    
    # Simulation / Evaluation metadata (excluded from live API scoring payload)
    is_fraud: Optional[bool] = None
    scenario: Optional[FraudScenario] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Transaction amount must be strictly positive.")
        return round(v, 2)
