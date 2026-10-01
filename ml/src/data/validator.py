"""Data Validation Engine for Payment Transaction Datasets.

Performs schema verification, anomaly boundary checks, temporal consistency
checks, and class imbalance metrics validation.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np


class DataValidationReport:
    """Encapsulates results from dataset validation checks."""

    def __init__(self):
        self.is_valid: bool = True
        self.total_records: int = 0
        self.fraud_count: int = 0
        self.fraud_ratio_pct: float = 0.0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.summary_stats: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "total_records": self.total_records,
            "fraud_count": self.fraud_count,
            "fraud_ratio_pct": self.fraud_ratio_pct,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary_stats": self.summary_stats,
        }


class DataValidator:
    """Validates payment transaction DataFrames against domain integrity constraints."""

    REQUIRED_COLUMNS = [
        "transaction_id",
        "timestamp",
        "customer_id",
        "merchant_id",
        "amount",
        "currency",
        "country",
        "city",
        "lat",
        "lon",
        "device_id",
        "payment_method",
        "merchant_category",
        "is_fraud",
    ]

    def validate(self, df: pd.DataFrame) -> DataValidationReport:
        report = DataValidationReport()
        report.total_records = len(df)

        if df.empty:
            report.is_valid = False
            report.errors.append("Dataset is completely empty.")
            return report

        # 1. Required Columns Check
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            report.is_valid = False
            report.errors.append(f"Missing required columns: {missing_cols}")
            return report

        # 2. Missing Values Check
        null_counts = df[self.REQUIRED_COLUMNS].isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0].to_dict()
        if cols_with_nulls:
            report.is_valid = False
            report.errors.append(f"Found null values in critical columns: {cols_with_nulls}")

        # 3. Amount Domain Checks
        invalid_amounts = (df["amount"] <= 0).sum()
        if invalid_amounts > 0:
            report.is_valid = False
            report.errors.append(f"Found {invalid_amounts} transactions with amount <= 0.")

        # 4. Coordinates Domain Checks
        invalid_lat = ((df["lat"] < -90.0) | (df["lat"] > 90.0)).sum()
        invalid_lon = ((df["lon"] < -180.0) | (df["lon"] > 180.0)).sum()
        if invalid_lat > 0 or invalid_lon > 0:
            report.is_valid = False
            report.errors.append(f"Found coordinate boundary errors: lat={invalid_lat}, lon={invalid_lon}")

        # 5. Timestamp & Temporal Consistency Checks
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            report.is_valid = False
            report.errors.append("Column 'timestamp' is not datetime type.")
        else:
            is_sorted = df["timestamp"].is_monotonic_increasing
            if not is_sorted:
                report.warnings.append("Dataset timestamps are not strictly monotonic increasing.")

        # 6. Fraud Class Imbalance Statistics
        report.fraud_count = int(df["is_fraud"].sum())
        report.fraud_ratio_pct = round(float(df["is_fraud"].mean() * 100.0), 3)

        if report.fraud_ratio_pct > 15.0:
            report.warnings.append(
                f"Fraud ratio is unusually high ({report.fraud_ratio_pct}%). "
                "Realistic production payment streams exhibit < 3% fraud."
            )
        elif report.fraud_ratio_pct < 0.1:
            report.warnings.append(
                f"Fraud ratio is extremely low ({report.fraud_ratio_pct}%). "
                "Evaluation sets require sufficient positive samples for PR-AUC."
            )

        # 7. Summary Statistics
        report.summary_stats = {
            "amount_min": float(df["amount"].min()),
            "amount_mean": round(float(df["amount"].mean()), 2),
            "amount_median": round(float(df["amount"].median()), 2),
            "amount_p95": round(float(df["amount"].quantile(0.95)), 2),
            "amount_max": float(df["amount"].max()),
            "unique_customers": int(df["customer_id"].nunique()),
            "unique_merchants": int(df["merchant_id"].nunique()),
            "unique_devices": int(df["device_id"].nunique()),
            "unique_countries": int(df["country"].nunique()),
            "date_start": str(df["timestamp"].min()),
            "date_end": str(df["timestamp"].max()),
        }

        return report
