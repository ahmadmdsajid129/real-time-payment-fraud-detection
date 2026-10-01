# Machine Learning Pipeline & Modeling Lifecycle

---

## 1. End-to-End ML Pipeline Architecture

The machine learning subsystem is engineered as an offline-to-online lifecycle ensuring zero temporal leakage, probability calibration, and transaction explainability:

```mermaid
graph TD
    DATA[Dataset / Synthetic Stream] --> VAL[Data Validation & Schema Checks]
    VAL --> EDA[Exploratory Data Analysis]
    EDA --> TSPLIT[Strict Temporal Splitting<br/>Train: Months 1-7 | Val: Month 8 | Test: Month 9]
    
    TSPLIT --> FE[Historical Feature Engineering<br/>No Future Retrospective Leakage]
    
    FE --> IMB[Imbalance Strategy<br/>scale_pos_weight & Cost Optimization]
    
    IMB --> BASE[Baseline Models<br/>Dummy & Logistic Regression]
    IMB --> TREE[Ensemble Models<br/>Random Forest & XGBoost]
    
    TREE --> CALIB[Probability Calibration<br/>Isotonic Regression & Platt Sigmoid]
    
    FE --> ANOM[Unsupervised Anomaly Model<br/>Isolation Forest]
    
    CALIB --> EVAL[Evaluation on Held-Out Test Set<br/>PR-AUC, ROC-AUC, Brier Score]
    ANOM --> EVAL
    
    EVAL --> SHAP_EXP[SHAP TreeExplainer Formulation]
    SHAP_EXP --> SERVE[Model Export & Registry Storage<br/>ml/models/saved/xgboost_v1.0.0.joblib]
```

---

## 2. Temporal Splitting & Leakage Prevention Strategy

### 2.1 The Danger of Random K-Fold Splitting
Random shuffling on payment transactions is a fatal flaw in fraud ML:
1. **Information Leakage**: Fraudsters repeat attacks across minutes or hours. Random splits place one transaction from an attack cluster into training and another into test, giving the model an unrealistic shortcut.
2. **Lookahead Bias**: Calculating customer rolling spending averages using both past and future transactions inflates test PR-AUC drastically while failing in production.

### 2.2 Chronological Split Protocol
Data is partitioned strictly by UTC timestamp:
- **Training Set (70%)**: $t \in [T_0, T_1)$ (Historical learning window)
- **Validation Set (15%)**: $t \in [T_1, T_2)$ (Hyperparameter optimization and calibration fitting)
- **Test Set (15%)**: $t \in [T_2, T_3)$ (Unseen future evaluation; frozen evaluation set)

---

## 3. Modeling Hierarchy & Comparative Analysis

| Model | Role | Inductive Bias / Mechanics | Strengths | Weaknesses |
| :--- | :--- | :--- | :--- | :--- |
| **Dummy Classifier** | Sanity Floor | Predicts prior majority class distribution ($P(\text{fraud}) \approx 0.015$). | Zero computational cost. | Zero discriminative capacity; baseline floor. |
| **Logistic Regression** | Interpretable Linear Baseline | Linear log-odds combination $\sigma(\mathbf{w}^T \mathbf{x} + b)$ with L2 regularization. | Convex loss, fast training, transparent weights. | Incapable of capturing non-linear feature interactions (e.g., high amount *only when* new country). |
| **Random Forest** | Non-Linear Ensemble Baseline | Bagging $B$ decorrelated decision trees with random feature subsampling. | Captures interactions; robust against variance. | High memory footprint at inference; slower scoring latency. |
| **XGBoost (Champion)** | Primary Classifier | Gradient boosted trees minimizing regularized objective with second-order Taylor expansion: $\mathcal{L}^{(t)} \approx \sum [g_i f_t(x_i) + \frac{1}{2} h_i f_t^2(x_i)] + \Omega(f_t)$. | State-of-the-art tabular accuracy, native handling of missing values, sub-10ms inference. | Susceptible to overfitting without regularization; uncalibrated raw margins. |

---

## 4. Class Imbalance Mitigation

Fraud datasets naturally exhibit extreme class imbalance ($\sim 1\%$ to $2\%$ positive incidence).

### Chosen Strategies:
1. **Algorithmic Cost-Weighting (`scale_pos_weight`)**:
   $$\text{scale\_pos\_weight} = \frac{N_{\text{negative}}}{N_{\text{positive}}}$$
   Scales gradients of positive fraud samples during tree node split evaluation, heavily penalizing false negatives.
2. **Threshold Tuning**:
   Rather than defaulting to $0.5$, optimal operational decision thresholds are chosen by maximizing the $F_\beta$ score ($\beta = 2$, prioritizing Recall over Precision) on the held-out validation set.
3. **Rejection of Blind SMOTE**:
   Synthetic Minority Over-sampling Technique (SMOTE) interpolates synthetic points between temporal transactions, generating fictitious events that violate natural velocity constraints and temporal distributions.

---

## 5. Probability Calibration

Tree-based ensembles (XGBoost, Random Forest) push predictions toward extreme values ($0$ and $1$) or cluster near split boundaries, outputting distorted pseudo-probabilities rather than true likelihoods.

### Calibration Algorithms:
1. **Platt Scaling (Sigmoid)**:
   $$P(y=1|f) = \frac{1}{1 + \exp(A \cdot f + B)}$$
   Fits logistic parameters $A$ and $B$ over validation margins $f$.
2. **Isotonic Regression (Non-parametric)**:
   Fits a piecewise non-decreasing step function minimizing squared error:
   $$\min \sum (y_i - \hat{p}_i)^2 \quad \text{subject to } \hat{p}_i \le \hat{p}_j \text{ whenever } f_i \le f_j$$
- Evaluated using **Brier Score** ($\frac{1}{N} \sum (\hat{p}_i - y_i)^2$) and **Reliability Diagrams** (10-bin calibration curves).

---

## 6. Unsupervised Anomaly Detection: Isolation Forest

Anomalies do not always equate to fraud (e.g., an executive purchasing international airfare), but anomalousness is an indispensable risk signal.
- **Algorithm**: Isolation Forest recursively partitions feature space with random axis-aligned splits.
- **Principle**: Outliers require substantially fewer splits to isolate than normal clustering points:
  $$s(x, n) = 2^{-\frac{E(h(x))}{c(n)}}$$
  Where $h(x)$ is path length and $c(n)$ is average path length of unsuccessful searches in a Binary Search Tree.
- Generates a normalized continuous anomaly score $S_{\text{anomaly}} \in [0, 1]$.

---

## 7. Model Evaluation Metrics (Why Accuracy Fails)

In a dataset with $99\%$ legitimate transactions, a trivial model predicting "always legitimate" yields $99\%$ accuracy while catching $0$ fraudsters. 

The engine evaluates models using imbalance-resilient metrics:
- **PR-AUC (Precision-Recall Area Under Curve)**: Primary ranking metric; reflects precision across all operational recall thresholds.
- **ROC-AUC**: Evaluates general ranking capability across all false positive rates.
- **Recall at Fixed Precision (e.g., Recall @ 80% Precision)**: Direct business measure of fraud caught while limiting analyst alert fatigue.
- **Brier Score**: Measures probability calibration accuracy ($0.0$ being perfect).

---

## 8. Explainability via SHAP (SHapley Additive exPlanations)

For every transaction processed by XGBoost, the engine computes TreeSHAP values:
$$f(x) = \phi_0 + \sum_{j=1}^M \phi_j(x)$$
Where $\phi_0$ is the baseline expected value over training data, and $\phi_j(x)$ represents the exact additive contribution of feature $j$.
- **Positive $\phi_j$**: Factors driving risk *up* (e.g., $+0.35$ for `amount_zscore = 4.2`).
- **Negative $\phi_j$**: Factors driving risk *down* (e.g., $-0.12$ for `is_known_device = 1`).
- SHAP vectors are persisted in PostgreSQL (`predictions.shap_positive_drivers`) and rendered as interactive waterfall plots in Next.js.
