# Machine Learning Experiment Registry

---

## 1. Experiment Registry Protocol
All experiments in this log follow rigorous scientific methodology:
- **Hypothesis**: The exact statistical or behavioral thesis being tested.
- **Methodology**: Algorithms, feature subsets, and loss functions tested.
- **Temporal Split**: Fixed time-series split ($T_{\text{train}} \le t_1 < T_{\text{val}} \le t_2 < T_{\text{test}}$).
- **Evaluation Metrics**: PR-AUC, ROC-AUC, Brier Score, and Recall @ 80% Precision.
- **Status**: Formulated, In-Progress, or Executed.

---

## 2. Quantitative Experiment Tracking Table

| ID | Title / Hypothesis | Primary Model | Calibration | Features Used | PR-AUC | ROC-AUC | Brier Score | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EXP-000** | Majority class prior floor | Dummy Classifier | None | All Features (30) | 0.0271 | 0.5000 | 0.0264 | Executed |
| **EXP-001** | Linear baseline with standard scaling | Logistic Regression (L2) | None | All Features (30) | 0.9222 | 0.9947 | 0.0320 | Executed |
| **EXP-002** | Non-linear tree ensemble baseline | Random Forest (100 trees) | None | All Features (30) | 0.9858 | 0.9989 | 0.0032 | Executed |
| **EXP-003** | Gradient boosted trees with scale_pos_weight | XGBoost (Champion) | None | All Features (30) | 0.9825 | 0.9990 | 0.0023 | Executed |
| **EXP-004** | Impact of behavioral feature enrichment | XGBoost | None | Payload + Behavioral (28 features) | Target +0.15 PR-AUC | Target +0.05 ROC-AUC | Target < 0.03 | Formulated |
| **EXP-005** | Class imbalance correction via `scale_pos_weight` | XGBoost | None | All Features (28 features) | Evaluate Recall | Evaluate PR-AUC | Target < 0.03 | Formulated |
| **EXP-006** | Probability calibration comparison (Platt vs. Isotonic) | XGBoost | Platt & Isotonic | All Features (30) | 0.9825 | 0.9990 | 0.0028 (ECE 0.0014) | Executed |
| **EXP-007** | Threshold optimization on F2 score vs. Expected Cost | Calibrated XGBoost | Isotonic | All Features (30) | F2 Thresh 0.070 | Cost Thresh 0.010 | Min Loss INR 1.6k | Executed |
| **EXP-008** | Unsupervised anomaly detection integration | Isolation Forest | N/A | Velocity + Amount (11) | Outlier Score | Corr +0.5820 | Fraud Mean 0.7233 | Executed |

---

## 3. Detailed Experiment Protocols

### EXP-001: Logistic Regression Baseline
- **Hypothesis**: A regularized linear classifier provides an interpretable lower benchmark but will fail to capture non-linear fraud indicators (e.g., high amount *only* when accompanied by an unfamiliar country).
- **Configuration**: `penalty='l2', C=1.0, solver='lbfgs', max_iter=1000`.
- **Target Comparison**: Sanity floor vs. Dummy majority class.

### EXP-004: Impact of Behavioral Feature Enrichment
- **Hypothesis**: Adding sliding-window customer features (Z-score, 1h velocity, new device indicator) will dramatically increase PR-AUC compared to evaluating transactions in isolation.
- **Independent Variable**: Feature set (7 raw features vs. 28 enriched behavioral features).
- **Leakage Safeguard**: Features calculated strictly on $t < \text{current\_timestamp}$.

### EXP-006: Probability Calibration (Isotonic vs. Platt Scaling)
- **Hypothesis**: Raw tree probabilities will show severe overconfidence at boundaries; Isotonic Regression on the validation set will reduce the Brier Score by $\ge 30\%$ without harming ranking order.
- **Evaluation**: Reliability diagram binning (10 deciles) and Expected Calibration Error (ECE).
