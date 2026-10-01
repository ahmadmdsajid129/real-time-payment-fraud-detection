# Risk Engine & Decision Policy Specification

---

## 1. Risk Engine Overview & Principles

The **Risk Decision Engine** is an arbitrating policy layer that synthesizes multiple heterogeneous risk signals into an interpretable **0 to 100 Risk Score** and maps it to a concrete business triage decision: **`APPROVE`**, **`REVIEW`**, or **`BLOCK`**.

### Core Principles
1. **Separation of Inference from Decisioning**: The machine learning classifier outputs a statistical probability ($P \in [0, 1]$). It does not decide whether a payment is approved or declined. Business policies, loss tolerance, review costs, and deterministic safeguards belong exclusively inside the Risk Engine.
2. **Multi-Factor Signal Synthesis**: A single model prediction is susceptible to edge cases. The Risk Engine balances supervised probability, unsupervised anomaly scores, behavioral volatility, and deterministic heuristic triggers.
3. **No Magic Hardcoding**: All weights, score multipliers, and decision boundaries are declared via configuration (`.env` / Pydantic settings).

---

## 2. Signal Inputs & Normalization Architecture

The Risk Engine receives four normalized input components, each bounded in $[0, 1]$:

```text
  ┌────────────────────────────────────────────────────────┐
  │ 1. Calibrated ML Probability (P_ml)                    │
  │    Isotonic-calibrated XGBoost output                  │
  └──────────────────────────┬─────────────────────────────┘
                             │
  ┌──────────────────────────▼─────────────────────────────┐
  │ 2. Normalized Anomaly Score (S_anomaly)                │
  │    Isolation Forest decision function mapped to [0, 1] │
  └──────────────────────────┬─────────────────────────────┘
                             │
  ┌──────────────────────────▼─────────────────────────────┐
  │ 3. Behavioral Volatility Score (S_behavior)            │
  │    Z-score deviation + Velocity bursts                 │
  └──────────────────────────┬─────────────────────────────┘
                             │
  ┌──────────────────────────▼─────────────────────────────┐
  │ 4. Deterministic Rule Score (S_rules)                  │
  │    Weighted penalty of triggered domain rules          │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │    Risk Engine Synthesizer │
               │   Composite Score (0-100) │
               └─────────────┬─────────────┘
                             │
                 ┌───────────┼───────────┐
                 ▼           ▼           ▼
              APPROVE      REVIEW      BLOCK
              (0-29.9)    (30-74.9)   (75-100)
```

---

## 3. Mathematical Formula for the Composite Risk Score

The final risk score $R \in [0, 100]$ is computed as:

$$R = 100 \times \min\left(1.0, \, \max\left(0.0, \, w_{\text{ML}} \cdot P_{\text{ML}} + w_{\text{anomaly}} \cdot S_{\text{anomaly}} + w_{\text{behavior}} \cdot S_{\text{behavior}} + w_{\text{rules}} \cdot S_{\text{rules}}\right)\right)$$

### Default Weight Configuration
$$\sum w_i = 1.0$$
- $w_{\text{ML}} = 0.55$ (Primary supervised discriminative signal)
- $w_{\text{anomaly}} = 0.15$ (Unsupervised structural outlier detector)
- $w_{\text{behavior}} = 0.15$ (Customer-level standard deviation & velocity burst)
- $w_{\text{rules}} = 0.15$ (Critical security & contextual rule triggers)

---

## 4. Deterministic Rule Engine Specifications

The rule engine acts as a safety harness. It evaluates deterministic boolean predicates and assigns normalized severity penalties:

| Rule Code | Trigger Condition | Severity Penalty | Primary Fraud Vector |
| :--- | :--- | :--- | :--- |
| `R01_IMPOSSIBLE_TRAVEL` | `travel_speed_kmh > 900` AND `geo_distance_km > 200` | $0.90$ | Session hijacking / Proxy routing |
| `R02_VELOCITY_BURST_1M` | `txn_count_1m >= 3` | $0.80$ | Automated bot testing / Credential stuffing |
| `R03_NEW_DEVICE_HIGH_AMOUNT` | `is_new_device == 1` AND `customer_amount_zscore > 3.0` | $0.75$ | Account Takeover (ATO) |
| `R04_NEW_COUNTRY_FIRST_TIME` | `is_new_country == 1` AND `amount > 5000` | $0.60$ | Cross-border card-not-present fraud |
| `R05_DEVICE_SHARING_ANOMALY` | `device_customer_count >= 4` | $0.85$ | Fraud syndicate device sharing |
| `R06_UNUSUAL_HOUR_LARGE_SPEND` | `is_unusual_hour == 1` AND `amount_to_avg_ratio > 5.0` | $0.50$ | Compromised card off-hours drain |
| `R07_HIGH_AMOUNT_ZSCORE` | `customer_amount_zscore >= 5.0` | $0.70$ | Extreme high-value anomaly |

$$S_{\text{rules}} = \min\left(1.0, \sum_{\text{rule} \in \text{Triggered}} \text{penalty}(\text{rule})\right)$$

---

## 5. Cost-Sensitive Decision Making & Threshold Optimization

### 5.1 Business Cost Matrix
Making a binary or ternary decision carries asymmetric financial costs:

| Decision | Actual Legitimate ($y = 0$) | Actual Fraud ($y = 1$) |
| :--- | :--- | :--- |
| **APPROVE** | $\$0$ (Normal interchange fee earned) | **False Negative Cost**: Total transaction amount lost + $\$25$ chargeback penalty fee. |
| **REVIEW** | Cost of human analyst review ($\approx \$4.00$) + mild customer friction. | Cost of review ($\$4.00$) + chargeback prevented (net positive). |
| **BLOCK** | **False Positive Cost**: Insulted customer lifetime value decay ($\approx \$35.00$) + lost interchange fee. | $\$0$ (Direct fraud loss prevented). |

### 5.2 Expected Cost Minimization Function
For a transaction of amount $A$ with predicted calibrated probability $p$:
$$\mathbb{E}[\text{Cost}_{\text{Approve}}] = p \cdot (A + C_{\text{chargeback}})$$
$$\mathbb{E}[\text{Cost}_{\text{Block}}] = (1 - p) \cdot C_{\text{insult}}$$
$$\mathbb{E}[\text{Cost}_{\text{Review}}] = C_{\text{analyst}} + (1 - p) \cdot C_{\text{friction}}$$

The optimal decision policy selects:
$$\text{Decision}^* = \arg\min_{d \in \{\text{Approve, Review, Block}\}} \mathbb{E}[\text{Cost}_d]$$

---

## 6. Worked Concrete Example

### Scenario: Account Takeover Attack
- **Customer**: `CUST-9921`
- **Customer Historical Baseline**: $\mu = ₹1,200$, $\sigma = ₹300$, Known Country: `IN`, Known Device: `DEV-PHONE-1`
- **Current Transaction**: Amount: $₹52,000$, Country: `SG`, Device: `DEV-NEW-888`, Time: 03:15 AM (Unusual Hour)

#### Step 1: Feature Calculation
- `amount_zscore` $= (52000 - 1200) / 300 = 169.3 \implies$ capped at normalized $1.0$
- `is_new_device` $= 1$
- `is_new_country` $= 1$
- `is_unusual_hour` $= 1$

#### Step 2: Component Signals
- Calibrated ML Probability ($P_{\text{ML}}$): $0.88$
- Isolation Forest Anomaly ($S_{\text{anomaly}}$): $0.82$
- Behavioral Volatility ($S_{\text{behavior}}$): $0.95$
- Triggered Rules:
  - `R03_NEW_DEVICE_HIGH_AMOUNT` ($0.75$)
  - `R04_NEW_COUNTRY_FIRST_TIME` ($0.60$)
  - `R06_UNUSUAL_HOUR_LARGE_SPEND` ($0.50$)
  - Sum penalties $= 1.85 \implies S_{\text{rules}} = 1.0$

#### Step 3: Composite Calculation
$$R = 100 \times [ (0.55 \times 0.88) + (0.15 \times 0.82) + (0.15 \times 0.95) + (0.15 \times 1.0) ]$$
$$R = 100 \times [ 0.484 + 0.123 + 0.1425 + 0.15 ] = 100 \times 0.8995 = 89.95$$

#### Step 4: Decision Triaging
- Risk Score $= 90.0 / 100 \ge 75.0 \implies$ **`BLOCK`**
- Decision emitted to Kafka topic `transactions.decisions` and stored in PostgreSQL with full audit record.
