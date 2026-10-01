# Exploratory Data Analysis (EDA) Report
**Evaluation Window**: 2026-01-01 00:00:18.445729+00:00 to 2026-01-02 12:55:55.100323+00:00 (1.54 days)

---

## 1. Class Imbalance & Volume
- **Total Transactions**: 15,000
- **Legitimate Transactions**: 14,663 (97.75%)
- **Fraudulent Transactions**: 337 (2.247%)
- **Class Imbalance Ratio**: 1:43

> **Imbalance Implication**:  
> A naive majority-class classifier predicting 'Legitimate' across all rows yields **97.75% accuracy** while catching zero fraudsters.  
> Accuracy is statistically useless here; the model evaluation MUST rely on **PR-AUC, Recall @ 80% Precision, and Brier Score**.

---

## 2. Monetary Distribution Comparison (Amount in INR)

| Metric | Overall Population | Legitimate Transactions | Fraudulent Transactions |
| :--- | :--- | :--- | :--- |
| **Mean** | ₹2,897.29 | ₹2,415.91 | ₹23,842.35 |
| **Median** | ₹1,495.76 | ₹1,485.69 | ₹6,860.83 |
| **95th Percentile** | ₹10,942.97 | ₹9,833.88 | ₹76,256.81 |
| **Max** | ₹556,031.58 | ₹46,563.38 | ₹556,031.58 |

Fraudulent transactions exhibit a substantially higher mean and extreme tail distribution due to account-takeover and high-value drain scenarios.

---

## 3. Entity Cardinality
- **Distinct Customers**: 1,000
- **Distinct Merchants**: 100
- **Distinct Devices**: 1,438
- **Distinct Countries**: 6
- **Distinct Cities**: 12

---

## 4. Merchant Category Risk Profile

| Category | Total Volume | Fraud Rate (%) |
| :--- | :--- | :--- |
| `DEPARTMENT_STORE` | 1,653 | 2.30% |
| `DIGITAL_WALLET_TRANSFER` | 1,116 | 2.24% |
| `ELECTRONICS` | 1,461 | 2.94% |
| `GAMING_CASINO` | 1,687 | 2.37% |
| `GAS_STATION` | 1,688 | 1.78% |
| `GROCERY` | 1,315 | 2.13% |
| `JEWELRY_LUXURY` | 1,979 | 3.13% |
| `RESTAURANT` | 2,048 | 1.37% |
| `UTILITIES` | 2,053 | 2.09% |

---
*Report generated automatically by `ml/src/data/eda.py`*
