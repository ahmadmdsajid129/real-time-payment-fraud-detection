"""Exploratory Data Analysis (EDA) Module for Fraud Detection Datasets.

Analyzes amounts, temporal distributions, geographic breakdowns, class imbalance,
and prints/exports formatted statistical reports.
"""

from typing import Dict, Any
import pandas as pd
import numpy as np


class ExploratoryDataAnalysis:
    """Computes comprehensive statistics and domain metrics for transaction datasets."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(self.df["timestamp"]):
            self.df["timestamp"] = pd.to_datetime(self.df["timestamp"])

    def compute_summary_report(self) -> Dict[str, Any]:
        """Calculates core statistical aggregations across the dataset."""
        df = self.df
        total_txns = len(df)
        fraud_txns = int(df["is_fraud"].sum())
        legit_txns = total_txns - fraud_txns
        fraud_rate_pct = (fraud_txns / total_txns) * 100.0

        # Amount statistics comparison
        legit_amounts = df[~df["is_fraud"]]["amount"]
        fraud_amounts = df[df["is_fraud"]]["amount"]

        # Temporal breakdown
        df["hour"] = df["timestamp"].dt.hour
        df["day_name"] = df["timestamp"].dt.day_name()

        hourly_fraud = df.groupby("hour")["is_fraud"].agg(["count", "mean"]).to_dict("index")
        category_fraud = df.groupby("merchant_category")["is_fraud"].agg(["count", "mean"]).to_dict("index")
        country_fraud = df.groupby("country")["is_fraud"].agg(["count", "mean"]).to_dict("index")

        return {
            "dataset_overview": {
                "total_transactions": total_txns,
                "legitimate_transactions": legit_txns,
                "fraudulent_transactions": fraud_txns,
                "fraud_rate_percentage": round(fraud_rate_pct, 3),
                "class_imbalance_ratio": f"1:{int(legit_txns / max(fraud_txns, 1))}",
                "start_time": str(df["timestamp"].min()),
                "end_time": str(df["timestamp"].max()),
                "duration_days": round((df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 86400, 2),
            },
            "amount_analysis": {
                "overall": {
                    "mean": round(float(df["amount"].mean()), 2),
                    "std": round(float(df["amount"].std()), 2),
                    "median": round(float(df["amount"].median()), 2),
                    "p75": round(float(df["amount"].quantile(0.75)), 2),
                    "p95": round(float(df["amount"].quantile(0.95)), 2),
                    "max": round(float(df["amount"].max()), 2),
                },
                "legitimate": {
                    "mean": round(float(legit_amounts.mean()), 2),
                    "median": round(float(legit_amounts.median()), 2),
                    "p95": round(float(legit_amounts.quantile(0.95)), 2),
                    "max": round(float(legit_amounts.max()), 2),
                },
                "fraudulent": {
                    "mean": round(float(fraud_amounts.mean()), 2),
                    "median": round(float(fraud_amounts.median()), 2),
                    "p95": round(float(fraud_amounts.quantile(0.95)), 2),
                    "max": round(float(fraud_amounts.max()), 2),
                },
            },
            "cardinality": {
                "unique_customers": int(df["customer_id"].nunique()),
                "unique_merchants": int(df["merchant_id"].nunique()),
                "unique_devices": int(df["device_id"].nunique()),
                "unique_countries": int(df["country"].nunique()),
                "unique_cities": int(df["city"].nunique()),
            },
            "category_breakdown": category_fraud,
            "country_breakdown": country_fraud,
        }

    def generate_markdown_report(self) -> str:
        """Renders the EDA summary as a formatted Markdown report."""
        report = self.compute_summary_report()
        ov = report["dataset_overview"]
        amt = report["amount_analysis"]
        card = report["cardinality"]

        md = f"""# Exploratory Data Analysis (EDA) Report
**Evaluation Window**: {ov['start_time']} to {ov['end_time']} ({ov['duration_days']} days)

---

## 1. Class Imbalance & Volume
- **Total Transactions**: {ov['total_transactions']:,}
- **Legitimate Transactions**: {ov['legitimate_transactions']:,} ({100 - ov['fraud_rate_percentage']:.2f}%)
- **Fraudulent Transactions**: {ov['fraud_count'] if 'fraud_count' in ov else ov['fraudulent_transactions']:,} ({ov['fraud_rate_percentage']:.3f}%)
- **Class Imbalance Ratio**: {ov['class_imbalance_ratio']}

> **Imbalance Implication**:  
> A naive majority-class classifier predicting 'Legitimate' across all rows yields **{100 - ov['fraud_rate_percentage']:.2f}% accuracy** while catching zero fraudsters.  
> Accuracy is statistically useless here; the model evaluation MUST rely on **PR-AUC, Recall @ 80% Precision, and Brier Score**.

---

## 2. Monetary Distribution Comparison (Amount in INR)

| Metric | Overall Population | Legitimate Transactions | Fraudulent Transactions |
| :--- | :--- | :--- | :--- |
| **Mean** | ₹{amt['overall']['mean']:,} | ₹{amt['legitimate']['mean']:,} | ₹{amt['fraudulent']['mean']:,} |
| **Median** | ₹{amt['overall']['median']:,} | ₹{amt['legitimate']['median']:,} | ₹{amt['fraudulent']['median']:,} |
| **95th Percentile** | ₹{amt['overall']['p95']:,} | ₹{amt['legitimate']['p95']:,} | ₹{amt['fraudulent']['p95']:,} |
| **Max** | ₹{amt['overall']['max']:,} | ₹{amt['legitimate']['max']:,} | ₹{amt['fraudulent']['max']:,} |

Fraudulent transactions exhibit a substantially higher mean and extreme tail distribution due to account-takeover and high-value drain scenarios.

---

## 3. Entity Cardinality
- **Distinct Customers**: {card['unique_customers']:,}
- **Distinct Merchants**: {card['unique_merchants']:,}
- **Distinct Devices**: {card['unique_devices']:,}
- **Distinct Countries**: {card['unique_countries']}
- **Distinct Cities**: {card['unique_cities']}

---

## 4. Merchant Category Risk Profile

| Category | Total Volume | Fraud Rate (%) |
| :--- | :--- | :--- |
"""
        for cat, stats in report["category_breakdown"].items():
            md += f"| `{cat}` | {stats['count']:,} | {stats['mean']*100:.2f}% |\n"

        md += "\n---\n*Report generated automatically by `ml/src/data/eda.py`*\n"
        return md
