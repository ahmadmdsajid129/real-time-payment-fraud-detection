# Model Card: Supervised Payment Fraud Classifier (XGBoost)

---

## 1. Model Details
- **Model Name**: `xgboost_fraud_detector`
- **Model Version**: `v1.0.0`
- **Architecture**: Gradient Boosted Decision Trees (XGBoost) with Isotonic Probability Calibration.
- **Model Developer**: Fraud Engine ML Team (Portfolio Simulation).
- **Date**: October 2026.
- **Artifact File**: `ml/models/saved/xgboost_v1.0.0.joblib`

---

## 2. Intended Use & Non-Intended Use

### Intended Use
- Real-time scoring of incoming e-commerce card-not-present payment transactions.
- Generating calibrated probabilities of fraud ($P \in [0, 1]$) for consumption by the downstream Risk Engine.
- Providing per-transaction feature attributions via TreeSHAP for fraud analyst review queues.

### Non-Intended Use
- Sole autonomous decider of account termination without human review or deterministic rule context.
- Underwriting credit limits, loan eligibility, or merchant risk tiering.
- Processing transactions outside the supported currency and geographic feature domains.

---

## 3. Training Data & Feature Inputs

### Dataset Description
- Evaluated on chronologically ordered payment transaction stream (or benchmark IEEE-CIS / PaySim adapted simulation).
- **Fraud Incidence (Class Imbalance)**: $\approx 1.5\%$ positive fraud cases.
- **Total Training Instances**: 100,000+ simulated events with realistic customer historical baselines.

### Feature Domain
- **Payload Features**: `amount`, `log_amount`, `currency`, `hour_of_day`, `day_of_week`.
- **Behavioral Context Features**: `customer_avg_amount`, `customer_std_amount`, `customer_amount_zscore`, `amount_to_avg_ratio`.
- **Velocity Features**: `txn_count_1m`, `txn_count_5m`, `txn_count_1h`, `txn_count_24h`, `amount_sum_1h`.
- **Geographic & Device Features**: `is_new_device`, `is_new_country`, `geo_distance_km`, `travel_speed_kmh`, `impossible_travel`.

---

## 4. Evaluation Methodology & Validation Protocol

- **Temporal Validation**: Data split chronologically into Train (70%), Validation (15%), and Test (15%). No random shuffling across time.
- **Imbalance Handling**: Loss function weighted with `scale_pos_weight = N_neg / N_pos`.
- **Probability Calibration**: Validation predictions calibrated using Isotonic Regression to eliminate extreme probability distortion.

### Benchmark Target Metrics (Evaluated on Held-Out Test Set)

| Metric | Target Floor | Formula / Definition |
| :--- | :--- | :--- |
| **PR-AUC** | $\ge 0.82$ | Area under the Precision-Recall curve (primary optimization goal). |
| **ROC-AUC** | $\ge 0.94$ | True Positive Rate vs. False Positive Rate across all thresholds. |
| **Recall @ 80% Precision** | $\ge 0.70$ | Proportion of fraud captured at acceptable operational analyst load. |
| **Brier Score** | $\le 0.025$ | Mean squared difference between predicted calibrated probability and true binary outcome. |

---

## 5. Quantitative Limitations & Known Biases

1. **Cold-Start Bias**: For new cardholders with zero historical transactions, behavioral metrics (`customer_amount_zscore`, `is_new_device`) default to population baselines, resulting in slightly lower discriminative power until 3–5 transactions are recorded.
2. **Seasonal Distortion**: Model trained on standard weekday/weekend spending patterns may show elevated false positive rates during high-velocity holiday shopping events (e.g., Diwali or Cyber Monday) without dynamic threshold scaling.
3. **Imbalanced Representation**: Fraud typologies with very low sample counts (e.g., rare merchant collusion) may be missed by supervised learning and rely on the Unsupervised Isolation Forest or Rule Engine.

---

## 6. Retraining & Governance Triggers

1. **Performance Trigger**: If sliding 7-day PR-AUC drops below $0.75$ on confirmed analyst dispute labels.
2. **Drift Trigger**: If Population Stability Index (PSI) on top 5 features exceeds $0.25$.
3. **Cadence**: Scheduled monthly retraining pipeline with Champion-Challenger shadow evaluation before deployment.
