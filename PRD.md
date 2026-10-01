# Product Requirements Document (PRD)
## Real-Time Payment Fraud Detection & Risk Engine

---

## 1. Executive Summary & Problem Statement

### 1.1 Problem
Modern electronic payment systems process billions of transactions where fraudulent actors continuously adapt tactics—including card-not-present (CNP) fraud, synthetic identity fraud, credential stuffing, velocity attacks, and account takeover (ATO). 
Standard static rule engines produce unacceptable rates of false positives (insulting genuine cardholders) or high false negatives (financial losses and chargeback fees). Conversely, isolated ML models evaluating transactions solely on instant transaction-level attributes (amount, currency, merchant) fail because fraud is intrinsically contextual: a ₹50,000 transaction is legitimate for a high-net-worth customer purchasing electronics, but highly anomalous for a customer whose 6-month historical mean is ₹1,200.

Effective fraud mitigation requires **low-latency real-time inference** that blends:
1. Instant transaction payload data,
2. Historical sliding-window behavioral features (spending velocity, geographical movement, device linkages),
3. Supervised classification with well-calibrated probabilities,
4. Unsupervised anomaly detection, and
5. Deterministic rule policies into an arbitrated **0–100 Risk Score** terminating in an automated decision (`APPROVE`, `REVIEW`, `BLOCK`).

### 1.2 Project Goal
To engineer a production-grade, end-to-end simulation of a real-time payment fraud detection and risk scoring engine demonstrating applied machine learning, distributed event streaming (Kafka), sub-millisecond in-memory state caching (Redis), durable transactional persistence (PostgreSQL), high-performance REST APIs (FastAPI), explainable AI (SHAP), and an interactive investigation frontend (Next.js).

---

## 2. Target Personas & Primary Stakeholders

| Persona | Role | Key Responsibilities & Needs |
| :--- | :--- | :--- |
| **Fraud Analyst** | Operations / Investigation | Investigates transactions flagged for `REVIEW`; inspects feature values, customer historical baselines, and SHAP explanation vectors; submits confirmed fraud/legitimate dispute labels. |
| **Risk Analyst / Policy Manager** | Risk Strategy | Defines risk score thresholds (Approve/Review/Block boundaries), tunes business rules (e.g., velocity ceilings, high-risk merchant categories), and evaluates cost curves (false-positive vs. false-negative trade-offs). |
| **ML Engineer / Applied Scientist** | Modeling & MLOps | Designs features without temporal leakage; trains, validates, and calibrates models; monitors data drift and prediction calibration; oversees challenger/champion versioning. |
| **System Operator / Platform Engineer** | Infrastructure & Reliability | Monitors Kafka topic lag, end-to-end transaction latency (p50/p95/p99), Redis memory consumption, error rates, and API availability via Prometheus and Grafana. |

---

## 3. Primary User Stories & System Use Cases

1. **UC-01: Ingestion & Idempotency Check**  
   The system ingests raw transaction events from Kafka (`transactions.raw`). Before processing, it verifies whether the transaction ID has been evaluated within a 24-hour window to prevent duplicate billing or split-decisioning.
2. **UC-02: Real-Time Behavioral Feature Retrieval**  
   The system retrieves rolling behavioral summaries from Redis (e.g., 1h velocity, 24h count, rolling mean amount, known devices, known countries) *prior* to recording the current transaction.
3. **UC-03: Machine Learning Inference**  
   The system passes enriched feature vectors through an ensemble of models (Logistic Regression baseline, Random Forest, XGBoost) to produce raw decision margins.
4. **UC-04: Probability Calibration**  
   Raw ML outputs are transformed via calibrated mapping (Isotonic Regression / Platt Scaling) so that a score of 0.85 mathematically corresponds to an 85% expected empirical probability of fraud.
5. **UC-05: Unsupervised Anomaly Detection**  
   An Isolation Forest model independently scores how structurally anomalous the transaction is compared to general population distributions, outputting a normalized anomaly score.
6. **UC-06: Deterministic Rule Evaluation**  
   The Rule Engine evaluates critical risk triggers (e.g., `IMPOSSIBLE_TRAVEL`, `NEW_DEVICE_AND_HIGH_AMOUNT`, `VELOCITY_SPIKE_1M`).
7. **UC-07: Multi-Factor Risk Scoring (0–100)**  
   The Risk Engine aggregates the calibrated ML probability, anomaly score, behavioral variance, and rule signals into a weighted 0–100 composite risk score.
8. **UC-08: Decision Triaging**  
   Based on risk thresholds, the system emits an automated decision:
   - `0 to 29.9`: **APPROVE** (Instant authorization)
   - `30.0 to 74.9`: **REVIEW** (Held in analyst queue or step-up authentication)
   - `75.0 to 100.0`: **BLOCK** (Declined immediately)
9. **UC-09: Explainability via SHAP**  
   For every evaluated transaction, TreeSHAP calculates the top positive and negative feature contributions driving the ML score, ensuring decisions can be audited and explained.
10. **UC-10: Durable Persistence & Audit Logging**  
    Transaction payload, enriched features, calibrated probability, SHAP vectors, risk score, and rule breakdown are recorded to PostgreSQL and published to Kafka (`transactions.decisions`).
11. **UC-11: Online Behavioral State Mutation**  
    Upon successful evaluation, Redis rolling counters, sets, and sliding windows are updated with the current transaction data.
12. **UC-12: Human Feedback Loop & Dispute Resolution**  
    Analysts inspect transactions in Next.js and submit ground-truth labels (`CONFIRMED_FRAUD` / `CONFIRMED_LEGITIMATE`), feeding into `transactions.feedback` for model retraining and drift calculation.

---

## 4. System Boundaries & Non-Functional Requirements (NFRs)

### 4.1 Non-Functional Requirements

- **Low Latency Target**:
  - Redis feature lookup: $< 2$ ms (p95)
  - ML Inference + SHAP: $< 25$ ms (p95)
  - End-to-end pipeline (Kafka in $\to$ Decision out): $< 60$ ms (p95)
  - API HTTP Response: $< 80$ ms (p95)
- **Data Leakage Prevention**:
  - Zero future information leakage. Behavioral state calculations must strictly exclude the current transaction timestamp.
  - Model cross-validation must use temporal splitting (e.g., split by chronological week/month).
- **Idempotency**: Duplicate transaction payloads with identical IDs must return the cached decision without double-counting state.
- **Explainability**: 100% of non-approved transactions must provide top feature contribution vectors.
- **Graceful Degradation**: If Redis is unreachable, the system must fall back to basic transaction-payload heuristics and flag the evaluation as `DEGRADED_MODE` rather than crashing.
- **Observability**: Prometheus metrics exported for request latency, consumer lag, throughput, decision breakdown, and fraud rate.

### 4.2 Out-of-Scope (Strict Exclusions)
- Real payment processing or live payment gateway integration (Stripe, Adyen, Razorpay).
- Connection to Visa, Mastercard, or real banking networks.
- Ingestion or storage of real credit card numbers (PANs), CVVs, passwords, or personal banking credentials.
- Formal PCI-DSS Level 1 audit compliance.
- Massive multi-region active-active distributed datacenters (this is a realistic single-cluster Dockerized portfolio architecture).

---

## 5. Acceptance Criteria

| Feature Area | Verification Criterion | Status |
| :--- | :--- | :--- |
| **Spec & Docs** | All 16 architecture/spec docs present, cross-referenced, and consistent with no empty placeholders. | Phase 0 |
| **Data & EDA** | Clean dataset or realistic generator producing temporal data with documented class imbalance ($< 2\%$ fraud). | Phase 1 |
| **Features** | $\ge 25$ features generated strictly using historical data with automated leakage verification tests. | Phase 2 |
| **Modeling** | Logistic Regression, Random Forest, and XGBoost trained on temporal split; evaluated on PR-AUC, ROC-AUC, Brier score. | Phases 3–5 |
| **Calibration** | Isotonic/Platt calibration applied; reliability curves demonstrate reduced Brier score. | Phase 6 |
| **Anomaly** | Isolation Forest provides an anomaly score independent of supervised labels. | Phase 8 |
| **Risk Engine** | Produces a bounded 0–100 score; unit tests prove $0 \le \text{score} \le 100$ and deterministic decision boundaries. | Phase 9 |
| **Streaming** | Kafka pipeline processes messages across raw, features, predictions, and decisions topics. | Phase 10 |
| **State** | Redis sliding windows store rolling customer velocity, amounts, and device/country sets. | Phase 11 |
| **API** | FastAPI exposes typed OpenAPI endpoints matching `docs/API.md` with Pydantic validation. | Phase 13 |
| **UI** | Next.js displays live incoming transactions, investigation view, SHAP charts, and customer behavioral profile. | Phase 14 |
| **Tests** | $\ge 90\%$ test coverage on core risk rules and feature transformations using `pytest`. | Phase 20 |
| **Docker** | `docker compose up` starts all infrastructure, backend, generator, and dashboard seamlessly. | Phase 21 |
