# Master Technical Interview Handbook: Production Real-Time Fraud Detection & Risk Engine
> **Author & Architect**: Ahmad Md Sajid  
> **Repository**: `ahmadmdsajid129/real-time-payment-fraud-detection`  
> **Document Purpose**: Complete, interview-ready technical reference with deep-dive architectural justifications, mathematical formulations, implementation trade-offs, and empirical production metrics. Designed for seamless printing and conversion to PDF.

---

<div style="page-break-after: always;"></div>

## Table of Contents
1. [Executive Summary & Architecture Whiteboard Walkthrough](#1-executive-summary--architecture-whiteboard-walkthrough)
2. [The Big "Why" Architectural Comparisons (Kafka, XGBoost, Redis, etc.)](#2-the-big-why-architectural-comparisons)
   - [Q1. Why Apache Kafka instead of RabbitMQ, AWS SQS, or Celery?](#q1-why-apache-kafka-instead-of-rabbitmq-aws-sqs-or-celery)
   - [Q2. Why XGBoost instead of Deep Learning (MLP/LSTM/Transformers) or LightGBM/CatBoost?](#q2-why-xgboost-instead-of-deep-learning-or-lightgbmcatboost)
   - [Q3. Why Redis instead of querying PostgreSQL directly for rolling features?](#q3-why-redis-instead-of-querying-postgresql-directly-for-rolling-features)
   - [Q4. Why a Dual-Database Architecture (Redis + PostgreSQL)?](#q4-why-a-dual-database-architecture-redis--postgresql)
   - [Q5. Why Isotonic Regression instead of Platt Sigmoid Scaling?](#q5-why-isotonic-regression-instead-of-platt-sigmoid-scaling)
   - [Q6. Why Isolation Forest instead of One-Class SVM or Autoencoders?](#q6-why-isolation-forest-instead-of-one-class-svm-or-autoencoders)
   - [Q7. Why TreeSHAP instead of KernelSHAP or LIME?](#q7-why-treeshap-instead-of-kernelshap-or-lime)
   - [Q8. Why decouple the Multi-Factor Risk Engine from the ML Model?](#q8-why-decouple-the-multi-factor-risk-engine-from-the-ml-model)
   - [Q9. Why FastAPI + Pydantic instead of Flask or Django?](#q9-why-fastapi--pydantic-instead-of-flask-or-django)
   - [Q10. Why React 19 + Tailwind CSS instead of Streamlit or Gradio?](#q10-why-react-19--tailwind-css-instead-of-streamlit-or-gradio)
   - [Q11. Why Synthetic Data Generator with 9 Scenarios instead of Kaggle Public Datasets?](#q11-why-synthetic-data-generator-with-9-scenarios-instead-of-kaggle-public-datasets)
3. [Statistical Foundations, Leakage & Imbalance](#3-statistical-foundations-leakage--imbalance)
4. [Feature Engineering, Kinematics & Cold-Start Bayesian Shrinkage](#4-feature-engineering-kinematics--cold-start-bayesian-shrinkage)
5. [In-Memory State, Redis Sliding Windows & Idempotency](#5-in-memory-state-redis-sliding-windows--idempotency)
6. [Supervised ML Modeling, Optimization & Regularization](#6-supervised-ml-modeling-optimization--regularization)
7. [Probability Calibration, Cost Matrices & Business Decisioning](#7-probability-calibration-cost-matrices--business-decisioning)
8. [Unsupervised Anomaly Detection & Behavioral Profiling](#8-unsupervised-anomaly-detection--behavioral-profiling)
9. [Explainability (TreeSHAP) & Forensic Operations](#9-explainability-treeshap--forensic-operations)
10. [Multi-Factor Risk Engine, Rule Policies & Cost Optimization](#10-multi-factor-risk-engine-rule-policies--cost-optimization)
11. [Streaming Pipeline, Kafka Partitioning & Chaos Resilience](#11-streaming-pipeline-kafka-partitioning--chaos-resilience)
12. [Relational Persistence, Entity Resolution & Syndicate Detection](#12-relational-persistence-entity-resolution--syndicate-detection)
13. [Frontend Engineering, Real-Time WebSockets & Analyst Workflows](#13-frontend-engineering-real-time-websockets--analyst-workflows)
14. [Observability, Population Stability Index (PSI) & Concept Drift](#14-observability-population-stability-index-psi--concept-drift)
15. [Security Hardening, OWASP Defense-in-Depth & Privacy Compliance](#15-security-hardening-owasp-defense-in-depth--privacy-compliance)
16. [Empirical Benchmarks, Scaling to 50k TPS & Technical Trade-offs](#16-empirical-benchmarks-scaling-to-50k-tps--technical-trade-offs)

---

<div style="page-break-after: always;"></div>

## 1. Executive Summary & Architecture Whiteboard Walkthrough

### The Master Whiteboard Walkthrough: 11-Step Lifecycle of a Transaction
When an interviewer says: *"Walk me through the lifecycle of a transaction from the card swipe to the merchant notification,"* deliver this structured response:

```
[Payment Terminal / Checkout]
         │ (HTTP REST / Ingestion)
         ▼
[FastAPI Gateway: /api/v1/score]
  ├─ Pydantic v2 Type & Boundary Validation (Rejects DoS inputs, negative amounts)
  ├─ SHA-256 Idempotency Key Verification (Deduplicates network retries)
  └─ Publishes JSON to Kafka: `transactions.raw` (Partitioned by customer_id)
         │
         ▼
[Step 1: Feature Enrichment Worker]
  ├─ Polls `transactions.raw`
  ├─ Queries Redis Sorted Sets (ZSET) for customer rolling spend windows (1m, 5m, 1h, 24h, 30d)
  ├─ Calculates kinematic spatial speed (Haversine formula between (lat1, lon1) & (lat2, lon2))
  ├─ Computes real-time Z-score relative to customer historical mean & standard deviation
  ├─ Strict Zero-Leakage Guarantee: Current transaction excluded from historical window
  └─ Emits enriched vector to Kafka: `transactions.features`
         │
         ▼
[Step 2: ML Inference & Explainability Worker]
  ├─ Polls `transactions.features`
  ├─ Runs compiled C++ XGBoost Champion ensemble -> Raw log-odds margin score
  ├─ Evaluates Isotonic Regressor -> Strictly calibrated posterior probability P(Fraud|X)
  ├─ Evaluates Unsupervised Isolation Forest -> Spatial anomaly score s in [0, 1]
  ├─ Executes in-process TreeSHAP Explainer -> Computes exact local Shapley attributions (Top + / - drivers)
  └─ Emits scored payload to Kafka: `transactions.predictions`
         │
         ▼
[Step 3: Multi-Factor Risk Decision Worker]
  ├─ Polls `transactions.predictions`
  ├─ Evaluates Composite Risk Score: R = 100 * (0.55*ML + 0.15*Anom + 0.15*Behav + 0.15*Rules)
  ├─ Runs Deterministic Hard-Rule Safeguards (Impossible Travel, Velocity Burst, Device Syndicate)
  ├─ Triages into Decision Tiers:
  │    ├─ APPROVE  (Score < 30)   -> Fast-path checkout (<65ms roundtrip)
  │    ├─ REVIEW   (Score 30-74)  -> Step-up MFA / Forensic Analyst Queue
  │    └─ BLOCK    (Score >= 75)  -> Immediate transaction decline
  ├─ Computes Expected Financial Cost Matrix (Cost of FN vs Cost of FP vs Review overhead)
  ├─ Writes ACID Transaction, Prediction & Decision audit records to PostgreSQL
  ├─ Updates Redis Online State Post-Decision (Adds current transaction to ZSET and known sets)
  └─ Publishes decision to `transactions.decisions` & Prometheus metrics scraped by Grafana
         │
         ▼
[Real-Time Forensic React 19 UI & Merchant Gateway]
  └─ Live WebSocket/Polling Feed renders risk badge, interactive TreeSHAP waterfall, and 1-click triage
```

---

<div style="page-break-after: always;"></div>

## 2. The Big "Why" Architectural Comparisons

### Q1. Why Apache Kafka instead of RabbitMQ, AWS SQS, or Celery?
- **SHORT ANSWER**: Kafka is a distributed, immutable commit log with partitioned customer serialization, durable on-disk replayability, and consumer group offset independence. RabbitMQ and Celery are memory-first AMQP task queues that degrade severely under massive transaction backlogs and do not support strict per-entity chronological replay.
- **DEEP EXPLANATION**:
  1. **Strict Partition Ordering per Customer**: Payment fraud velocity checks require evaluating transactions chronologically per customer. In Kafka, messages with `key = customer_id` always hash to the exact same partition. A single partition consumer processes that customer's events strictly in sequence, eliminating race conditions. In RabbitMQ, round-robin worker delivery causes race conditions across concurrent workers.
  2. **Backpressure & Disk Buffering**: During attack spikes (e.g., automated card testing hitting 10,000 TPS), downstream ML inference and database writes may experience latency surges. Kafka persists messages to sequential disk pages (pagecache), absorbing millions of queued events without consuming worker RAM. RabbitMQ stores messages in RAM; when memory limits are reached, RabbitMQ blocks producers via flow control, choking the payment gateway.
  3. **Multi-Consumer Replayability**: In our architecture, the same transaction stream must be consumed by: (a) Feature Service, (b) Audit Logging to PostgreSQL, (c) Prometheus observability metrics, and (d) Shadow Challenger models. In Kafka, each consumer group maintains its own independent offset pointer into the immutable log. In Celery/RabbitMQ, consuming a task removes it from the queue, requiring complex fan-out exchanges and duplicating network payloads.
  4. **Delayed Chargeback Retraining**: When a chargeback arrives 45 days later, Kafka log offsets or event logs enable replaying past sequences to reconstruct model state without data drift.
- **TRADE-OFF MATRIX**:

| Capability | Apache Kafka (Selected) | RabbitMQ | Celery (Redis Broker) | AWS SQS |
| :--- | :--- | :--- | :--- | :--- |
| **Storage Architecture** | Immutable append-only log on disk | Volatile in-memory AMQP queue | In-memory Redis list/sorted set | Distributed managed cloud queue |
| **Throughput Capacity** | 100k+ msg/sec per broker | 15k–25k msg/sec (memory bound) | 5k–10k tasks/sec | Managed (pay per API call) |
| **Partition Ordering** | Guaranteed by `hash(customer_id)` | Round-robin (race conditions) | Non-deterministic worker race | FIFO queue limited to 3k TPS |
| **Replayability** | Rewind consumer offset to any time | Destructive read (acknowledged = lost) | Destructive read | Destructive read |
| **Backpressure Resilience** | Zero latency impact on ingestion | Producers throttled if RAM full | Redis OOM crash risk | Cloud throttles / cost explosion |

- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `services/streaming_client.py`, configured in `docker-compose.yml`, and documented in `docs/STREAMING.md` and ADR-001 in `docs/DECISIONS.md`.

---

### Q2. Why XGBoost instead of Deep Learning or LightGBM/CatBoost?
- **SHORT ANSWER**: XGBoost provides the optimal balance of tabular inductive bias, sub-10ms compiled C++ inference latency, robust performance on extreme class imbalance ($98.4\%$ legitimate vs $1.6\%$ fraud), and exact polynomial-time TreeSHAP explainability required by financial regulations (FCRA/ECOA).
- **DEEP EXPLANATION**:
  1. **Tabular Inductive Bias vs Deep Learning**: Tabular payment data consists of heterogeneous, unaligned feature types (discrete categorical country codes, continuous transaction amounts, skewed spatial speeds, rolling counts). Deep neural networks (MLPs, TabNet, Transformers) lack spatial or temporal invariance on tabular features, require heavy scaling/normalization, and tend to overfit sparse categorical distributions. Gradient Boosted Decision Trees (GBDT) naturally carve axis-aligned orthogonal decision boundaries, making them mathematically superior on tabular structures.
  2. **Inference Latency SLA**: In payment processing, the entire fraud evaluation SLA is sub-100ms. Deep learning models require tensor allocations and GPU execution (or slow CPU matrix multiplications of 35–80ms). In contrast, compiled XGBoost models execute in **$< 8$ ms** on standard CPU instances via tree traversal routines without requiring specialized GPU accelerators.
  3. **Class Imbalance Handling**: With a $1.6\%$ fraud rate, standard cross-entropy loss causes gradient starvation for minority instances. XGBoost provides `scale_pos_weight = N_neg / N_pos`, which scales the loss gradients for fraud instances directly during split finding. In our held-out temporal evaluation, Champion XGBoost achieved **PR-AUC = 0.9825** and **F1 = 0.9431**, outperforming Random Forest (0.9542) and Logistic Regression (0.7180).
  4. **Why XGBoost over LightGBM or CatBoost?**:
     - *LightGBM* uses leaf-wise (best-first) tree growth. While fast to train on 10M+ rows, leaf-wise growth easily overfits on deep unbalanced paths in financial anomaly data. XGBoost’s depth-wise growth with second-order Taylor regularization ($\gamma$ leaf penalty and $\lambda$ L2 leaf weight penalty) produced more stable generalization on temporal test splits.
     - *CatBoost* is excellent for high-cardinality categoricals, but has a significantly larger serialized model footprint and slower raw C++ scoring speed compared to XGBoost on numerical/kinematic velocity features.
  5. **Explainability Compliance**: Legal regulations (FCRA Adverse Action notices) mandate explaining *why* a customer was declined. XGBoost is natively integrated with TreeSHAP ($O(TLD^2)$ polynomial time). Neural networks require KernelSHAP or integrated gradients, which take seconds per sample and are too slow for real-time transactions.
- **WHERE IT APPEARS IN THIS PROJECT**: Champion model trained in `ml/train_xgboost.py`, evaluated in `ml/src/models/xgboost_model.py`, benchmarked in `docs/EXPERIMENTS.md` (EXP-004), and serialized at `ml/models/saved/xgboost_champion.joblib`.

---

### Q3. Why Redis instead of querying PostgreSQL directly for rolling features?
- **SHORT ANSWER**: PostgreSQL disk reads and aggregate queries (`COUNT(*)`, `AVG(*)`) take 15–50 ms under concurrent load, which violates our sub-60ms p95 latency budget. Redis serves in-memory sorted set queries in $< 0.8$ ms with $O(\log N + M)$ complexity.
- **DEEP EXPLANATION**:
  1. **The Latency Budget**: A real-time payment gateway allocates no more than 60–100ms for total fraud evaluation. If the feature store consumes 35ms querying relational tables, the downstream ML inference, SHAP explanation, and network transit will breach the timeout SLA, causing payment drops. Redis in-memory lookups return in **$< 1$ ms**.
  2. **The Aggregation Bottleneck**: Calculating rolling features (e.g., *"How many transactions has Customer A made in the last 5 minutes?"* and *"What is their 24-hour total spend?"*) requires indexed range queries in PostgreSQL:
     ```sql
     SELECT COUNT(*), SUM(amount) FROM transactions 
     WHERE customer_id = 'CUST-101' AND timestamp >= NOW() - INTERVAL '5 minutes';
     ```
     At 1,000 TPS across 100,000 active cardholders, PostgreSQL suffers catastrophic index contention, buffer cache thrashing, and connection pool starvation.
  3. **Redis Sorted Sets (`ZSET`) Sliding Windows**: Redis stores timestamps as the numeric floating-point `score` and transaction details as the `member`. Evicting expired transactions and counting recent ones requires two single-digit microsecond commands:
     ```text
     ZREMRANGEBYSCORE cust:101:window -inf (now - 3600)  # Evict txns older than 1 hr
     ZCOUNT cust:101:window (now - 300) +inf             # Count txns in last 5 mins: O(log N)
     ```
  4. **Atomic Set Operations for Known Entities**: Checking whether a device or country has ever been seen for a customer is an $O(1)$ set membership test: `SISMEMBER cust:101:devices DEV-01`.
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `services/feature_service/redis_state.py`, verified in `tests/unit/test_redis_state.py`, and documented in `docs/DATABASE.md` and ADR-002 in `docs/DECISIONS.md`.

---

### Q4. Why a Dual-Database Architecture (Redis + PostgreSQL)?
- **SHORT ANSWER**: Redis provides sub-millisecond volatile in-memory state for real-time feature extraction; PostgreSQL provides ACID-compliant durable storage, complex relational joins, and immutable JSONB audit history required for dispute investigations and compliance.
- **DEEP EXPLANATION**:
  - Neither database can replace the other without catastrophic architectural compromises:
    - If you use **Only PostgreSQL**: System throughput caps at a few hundred TPS due to disk I/O bottlenecks during sliding-window aggregations; p95 latency exceeds 120ms.
    - If you use **Only Redis**: RAM cost becomes astronomical for 5 years of historical transaction logs ($100\text{GB}+$). Furthermore, Redis lacks SQL relational joins (e.g., joining transactions to fraud dispute outcomes and analyst notes), lacks ACID multi-table transactions, and has weak durability guarantees during cluster failovers.
  - **Data Responsibility Separation**:
    - **Redis (Hot Path)**: 30-day sliding windows (`ZSET`), known device sets (`SET`), idempotency token locks (`STRING` with TTL).
    - **PostgreSQL (Cold / Audit Path)**: Complete financial ledger (`transactions`), model outputs and latencies (`predictions`), triggered business rules (`risk_decisions`), and forensic analyst audit notes (`feedback`).
- **WHERE IT APPEARS IN THIS PROJECT**: Defined in `docs/DATABASE.md`, schema in `database/schema.sql`, connection pools in `database/connection.py`, and ADR-003 in `docs/DECISIONS.md`.

---

### Q5. Why Isotonic Regression instead of Platt Sigmoid Scaling?
- **SHORT ANSWER**: Gradient boosted ensembles output non-linear, multi-modal log-odds margins that violate the strict parametric sigmoid assumption of Platt Scaling. Isotonic Regression fits a non-parametric, monotonic step-wise mapping that achieved superior calibration with an Expected Calibration Error of **$\text{ECE} = 0.0014$** and Brier Score of **$0.0055$**.
- **DEEP EXPLANATION**:
  1. **The Uncalibrated Margin Problem**: XGBoost with `scale_pos_weight=60.5` deliberately shifts margin predictions toward positive logits to aggressively separate fraud. While this preserves rank ordering (high ROC-AUC), the raw sigmoid outputs $\hat{p} = \sigma(z)$ are heavily skewed toward $1.0$. A raw score of $0.85$ does not mean there is an $85\%$ chance of fraud; in reality, only $12\%$ of transactions with that score are fraudulent.
  2. **Platt Scaling (Parametric Logistic)**: Platt scaling fits a logistic curve $P(y=1|f) = \frac{1}{1 + \exp(Af + B)}$. If the raw scores have clusters or non-sigmoid plateaus (common in tree models where leaves group samples into discrete steps), Platt scaling under-calibrates the critical middle range ($0.30 - 0.70$), which is exactly where human review triage decisions occur.
  3. **Isotonic Regression (Non-Parametric)**: Isotonic regression solves a monotonic least-squares optimization problem:
     $$\min \sum (y_i - \hat{y}_i)^2 \quad \text{subject to } \hat{y}_i \le \hat{y}_j \text{ whenever } f_i \le f_j$$
     It uses the Pair Adjacent Violators (PAV) algorithm to produce a flexible, step-wise monotonic calibration curve without assuming any predetermined mathematical distribution.
  4. **Empirical Results in This Project**:
     - *Raw XGBoost*: $\text{ECE} = 0.0842, \text{Brier} = 0.0189$
     - *Platt Scaling*: $\text{ECE} = 0.0098, \text{Brier} = 0.0092$
     - *Isotonic Regressor (Champion)*: **$\text{ECE} = 0.0014, \text{Brier} = 0.0055$** (Over $6\times$ better calibration).
- **WHERE IT APPEARS IN THIS PROJECT**: Calibrator in `ml/src/calibration/calibrator.py`, training script in `ml/train_calibration.py`, test verification in `tests/unit/test_calibration.py`, and serialized artifact at `ml/models/saved/calibrator_isotonic.joblib`.

---

### Q6. Why Isolation Forest instead of One-Class SVM or Autoencoders?
- **SHORT ANSWER**: Isolation Forest has linear time complexity $O(n \cdot t \cdot \psi)$ and sub-millisecond inference latency ($< 0.5$ ms). One-Class SVM has quadratic/cubic complexity $O(n^2 - n^3)$, and Deep Autoencoders require heavy GPU/CPU tensor backpropagation that exceeds our latency budget.
- **DEEP EXPLANATION**:
  1. **Algorithmic Principle of Isolation**: Outliers are few and statistically distinct in feature space. Isolation Forest builds an ensemble of Extremely Randomized Trees ($iTrees$). Because anomalies have extreme values, they are isolated near the root of the tree with very short path lengths $h(x)$. Normal clustered instances require deep recursive partitioning.
  2. **Computational Complexity**:
     - *One-Class SVM*: Solving the dual quadratic programming problem requires computing the kernel matrix ($O(n^2)$ to $O(n^3)$). Scoring a new transaction requires calculating kernel distances across all support vectors, taking 15–30 ms per transaction.
     - *Deep Autoencoder*: Requires tensor reconstruction error calculations $\|x - \hat{x}\|_2^2$, taking 20–50 ms on CPU.
     - *Isolation Forest*: Scoring requires traversing 100 shallow trees ($t=100$) of max depth $\approx \log_2(\psi) = 8$. This executes in **$< 0.5$ ms** on CPU.
  3. **Orthogonal Signal to Supervised Model**: Supervised models only detect fraud patterns that were present in historical training labels (known attack vectors). When a fraud syndicate invents a completely novel attack technique (Zero-Day fraud), XGBoost may output a low fraud probability. However, Isolation Forest flags the unusual feature combination as a statistical outlier ($s > 0.65$), raising the multi-factor risk score to route the event to human review.
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `ml/src/anomaly/isolation_forest.py`, trained in `ml/train_anomaly.py`, unit tested in `tests/unit/test_anomaly.py`, and artifact saved at `ml/models/saved/isolation_forest_detector.joblib`.

---

### Q7. Why TreeSHAP instead of KernelSHAP or LIME?
- **SHORT ANSWER**: TreeSHAP computes exact Shapley attributions in polynomial time $O(T \cdot L \cdot D^2)$ by traversing tree structure directly. KernelSHAP and LIME rely on exponential random sampling approximations that take seconds per prediction, making them impossible for real-time transaction scoring.
- **DEEP EXPLANATION**:
  1. **The Game Theory Guarantee**: Shapley values from cooperative game theory are the *only* attribution method that satisfies four fundamental axioms:
     - *Efficiency*: $\sum \phi_i = f(x) - E[f(X)]$ (Attributions sum exactly to the prediction difference).
     - *Symmetry*: Identical features receive identical attributions.
     - *Dummy*: Features with no impact receive zero attribution.
     - *Additivity*: Attributions across ensemble trees can be summed linearly.
  2. **Computational Speed**:
     - *LIME*: Fits an interpretable linear surrogate model by perturbing the input vector hundreds of times. Takes $300 - 800$ ms per transaction and produces non-deterministic explanations.
     - *KernelSHAP*: Estimates Shapley values via weighted bivariate regression over $2^{|M|}$ feature subsets. Takes $1,500 - 4,000$ ms per transaction.
     - *TreeSHAP*: Traverses internal tree nodes directly in C++, computing conditional expectations across all paths simultaneously in **$15 - 30$ ms**.
  3. **Forensic Operations Utility**: When an analyst investigates a blocked transaction, TreeSHAP provides the exact mathematical drivers: e.g., `amount_zscore = +3.8` ($+0.32$), `country_is_new = 1` ($+0.21$), `txn_count_1h = 4` ($+0.18$), giving immediate forensic clarity for customer phone support.
- **WHERE IT APPEARS IN THIS PROJECT**: Evaluated in `services/inference_service/consumer.py`, returned via `/api/v1/transactions/{id}/explanation`, and rendered as interactive waterfall charts in the React 19 UI.

---

### Q8. Why decouple the Multi-Factor Risk Engine from the ML Model?
- **SHORT ANSWER**: ML models output statistical estimates; business rules, compliance laws (e.g., OFAC sanctions, AML mandates), and company risk appetites change rapidly without retraining cycles. Decoupling allows instant policy adjustments in seconds without ML model retraining or redeployment.
- **DEEP EXPLANATION**:
  1. **Compliance Overrides**: If an international sanction list or regulatory velocity cap changes (e.g., mandatory step-up authentication on transactions exceeding ₹50,000 or from sanctioned jurisdictions), an ML model cannot guarantee a deterministic block. Deterministic business rules provide $100\%$ legal compliance guarantees.
  2. **Dynamic Risk Appetite**: On Black Friday, a retailer's primary objective is maximizing checkout conversion; they may raise the block threshold from 75 to 85 to prevent insulting VIP shoppers. Conversely, during an active bot credential-stuffing attack, the risk threshold can be dialed down to 60. Decoupled configuration enables these shifts via dynamic environment variables or configuration APIs in $< 1$ second.
  3. **Multi-Factor Triangulation**: The Risk Engine synthesizes four distinct signals:
     $$R = 100 \times \min\left(1.0, 0.55 P_{\text{ML}} + 0.15 S_{\text{anom}} + 0.15 S_{\text{behav}} + 0.15 S_{\text{rules}}\right)$$
     This prevents single-point model failures: if the ML model is uncertain ($P_{\text{ML}} = 0.25$), but the behavioral score is extreme ($S_{\text{behav}} = 0.90$) due to impossible travel, the composite score appropriately triggers human review.
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `services/risk_engine/engine.py`, rules in `services/risk_engine/rules.py`, and verified in `tests/unit/test_risk_engine.py`.

---

### Q9. Why FastAPI + Pydantic instead of Flask or Django?
- **SHORT ANSWER**: FastAPI provides native asynchronous I/O (`asyncio`) on an ASGI server (`uvicorn`), sub-millisecond routing, automated Pydantic v2 data validation that blocks malformed inputs before reaching memory, and automated OpenAPI documentation.
- **DEEP EXPLANATION**:
  - *Flask*: Built on WSGI, which is synchronous and blocking. Every concurrent payment request ties up an entire OS thread. Under 500 concurrent connections, thread pool exhaustion causes latency degradation ($> 200$ ms).
  - *Django*: Monolithic framework with extensive ORM overhead, template engines, and session middleware unnecessary for a microsecond streaming API.
  - *FastAPI*: Runs on Starlette and uvloop. Non-blocking asynchronous database and Redis I/O allow a single lightweight worker process to handle thousands of concurrent requests with minimal RAM ($< 80\text{MB}$). Pydantic v2 (compiled in Rust) parses and validates JSON payloads in microseconds.
- **WHERE IT APPEARS IN THIS PROJECT**: API entry point in `services/api/main.py`, route definitions in `services/api/routes.py`, and schemas in `services/api/schemas.py`.

---

### Q10. Why React 19 + Tailwind CSS instead of Streamlit or Gradio?
- **SHORT ANSWER**: Streamlit and Gradio re-execute entire Python scripts on every interaction, causing multi-second page re-renders, high server memory usage, and zero support for sub-second live streaming feeds. React 19 + Tailwind CSS provides a production-grade, client-side virtual DOM with sub-100ms optimistic UI updates, persistent WebSocket feeds, and interactive forensic toolbars.
- **DEEP EXPLANATION**:
  - Streamlit is designed for static data science prototypes, not 24/7 fraud operations rooms where analysts triage live transaction streams under severe time pressure.
  - Our React 19 dashboard maintains an in-memory sliding buffer of the 30 most recent transactions, updates KPI metrics optimistically, renders interactive SVG TreeSHAP attribution waterfalls, and provides a 1-click live attack scenario simulator toolbar mounted directly under `/dashboard`.
- **WHERE IT APPEARS IN THIS PROJECT**: Component hierarchy in `frontend/src/`, production assets built to `frontend/dist`, and mounted in FastAPI in `services/api/main.py`.

---

### Q11. Why Synthetic Data Generator with 9 Scenarios instead of Kaggle Public Datasets?
- **SHORT ANSWER**: Public datasets (e.g., Kaggle CreditCardFraud, IEEE-CIS) are static, anonymized with PCA components ($V_1 - V_28$), and strip away critical temporal timestamps, real IP addresses, and device fingerprints. Our synthetic generator models realistic multi-entity networks with 9 distinct fraud attack typologies across chronological sequences.
- **DEEP EXPLANATION**:
  1. **Anonymized PCA Destroys System Design**: You cannot calculate Haversine distance, impossible travel speed, device sharing ratios, or rolling 1-hour transaction velocities on anonymous PCA columns like $V_14$ and $V_17$.
  2. **Dynamic Attack Typologies**: Our generator simulates realistic behavioral patterns:
     - Scenario 1: Normal cardholder baseline (Poisson arrival, Gaussian amount).
     - Scenario 2: Velocity Card Testing (rapid micro-transactions within seconds).
     - Scenario 3: Impossible Travel (London $\to$ Singapore in 30 minutes, $> 900$ km/h).
     - Scenario 4: Account Takeover / ATO (abrupt 5x spending deviation + new device).
     - Scenario 5: High-Amount Sudden Spike ($> 4.0$ historical Z-score).
     - Scenario 6: Organized Device Syndicate (single device shared across 5+ accounts).
     - Scenario 7: Unfamiliar Country Incursion.
     - Scenario 8: Late Night Dormant Account Activation.
     - Scenario 9: Repeated Declined Micro-Transactions.
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `ml/src/data/synthetic_generator.py` and `services/transaction_generator/producer.py`.

---

<div style="page-break-after: always;"></div>

## 3. Statistical Foundations, Leakage & Imbalance

### Q12. What is Temporal Data Leakage, and how is it strictly prevented in this project?
- **SHORT ANSWER**: Leakage occurs when future information or concurrent transaction statistics contaminate the features used for past predictions. We mathematically enforce zero leakage by splitting chronologically and updating Redis state strictly *after* risk decisioning.
- **DEEP EXPLANATION**:
  1. **The Train-Val-Test Chronological Cut**:
     - Never use random k-fold cross-validation. We split data chronologically:
       $$\text{Train } (t \le T_1) \quad \to \quad \text{Val } (T_1 < t \le T_2) \quad \to \quad \text{Test } (t > T_2)$$
  2. **Strict Ex-Ante Behavioral Aggregations**:
     - When computing customer rolling average spend $\mu_{t}$ for transaction $x_t$ arriving at timestamp $T$, the rolling aggregation window must strictly include transactions where $t_{\text{prev}} < T$.
     - If $x_t$ is included in its own mean or standard deviation calculation, the Z-score feature is artificially suppressed, creating overly optimistic offline test performance that fails in production.
  3. **Operational Enforcement in Streaming**:
     - In `services/feature_service/consumer.py`, historical lookups query Redis using `before_timestamp_epoch = t_curr`.
     - In `services/risk_engine/consumer.py`, `state_manager.update_state_post_decision()` is invoked only **after** the risk decision has been rendered.
- **WHERE IT APPEARS IN THIS PROJECT**: Verified by regression test `tests/unit/test_features.py::test_zero_temporal_leakage_guarantee` and documented in `docs/FEATURE_ENGINEERING.md`.

---

### Q13. Why is Accuracy misleading, and how do you evaluate an imbalanced fraud model?
- **SHORT ANSWER**: Accuracy treats false positives and false negatives equally. When legitimate transactions are $98.4\%$, a trivial model predicting "always legitimate" gets $98.4\%$ accuracy while missing $100\%$ of fraud. We evaluate PR-AUC, Recall at fixed False-Positive Rate ($< 1\%$), and Brier Score.
- **DEEP EXPLANATION**:
  - The confusion matrix in fraud detection has asymmetric financial and operational costs:
    - **False Negative (FN)**: Fraud approved $\to$ Financial chargeback loss ($100\%$ of transaction amount) plus bank dispute fees ($\$15 - \$25$) and merchant reputation penalty.
    - **False Positive (FP)**: Legitimate cardholder blocked $\to$ Customer insult, abandoned shopping cart, lifetime brand churn, and forensic analyst review overhead ($\$3 - \$5$).
  - **Metrics Used**:
    - **PR-AUC**: Measures the area under the Precision-Recall curve. Unlike ROC-AUC, PR-AUC does not include True Negatives in its denominator, making it acutely sensitive to false positive spikes.
    - **Recall @ FPR $\le 0.5\%$**: What percentage of fraud is captured while insulting no more than 5 in 1,000 legitimate customers?
    - **Brier Score**: Evaluates probability calibration accuracy: $\text{BS} = \frac{1}{N} \sum (\hat{p}_i - y_i)^2$.

---

<div style="page-break-after: always;"></div>

## 4. Feature Engineering, Kinematics & Cold-Start Bayesian Shrinkage

### Q14. How do you handle Cold-Start customers with 0 or 1 historical transactions? (Bayesian Shrinkage)
- **SHORT ANSWER**: We apply Empirical Bayesian Shrinkage, pulling sparse individual customer estimates toward the global population prior based on transaction count maturity $N$.
- **DEEP EXPLANATION**:
  - For a new cardholder with only $N=1$ transaction of $\$500$, their sample standard deviation is undefined and sample mean is unreliable. Computing a standard Z-score would result in division by zero or extreme instability.
  - We define a shrinkage weighting formula:
    $$\hat{\mu}_{\text{shrunk}} = \frac{N}{N + K} \bar{x}_{\text{cust}} + \frac{K}{N + K} \mu_{\text{global}}$$
    $$\hat{\sigma}^2_{\text{shrunk}} = \frac{N}{N + K} s^2_{\text{cust}} + \frac{K}{N + K} \sigma^2_{\text{global}}$$
    Where $K=5$ is the empirical shrinkage strength parameter.
  - When $N=0$ (Brand new customer): $\hat{\mu} = \mu_{\text{global}}$. The customer is evaluated against the general population profile.
  - As $N \to \infty$ (Mature customer): $\hat{\mu} \to \bar{x}_{\text{cust}}$. The estimate smoothly converges to their personal spending baseline.
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `services/risk_engine/entity_resolution.py` and unit tested in `tests/unit/test_entity_resolution.py::test_bayesian_shrinkage_cold_start`.

---

### Q15. How do you detect "Impossible Travel" in real time using the Haversine formula?
- **SHORT ANSWER**: We calculate great-circle spatial distance between the current and immediately preceding transaction coordinates, divide by elapsed time, and flag speeds exceeding commercial aviation thresholds ($> 900$ km/h).
- **DEEP EXPLANATION**:
  - Great-circle distance calculation via the Haversine equation:
    $$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
    $$d = 2 R \cdot \arcsin\left(\sqrt{a}\right)$$
    Where $\phi$ is latitude in radians, $\lambda$ is longitude, and $R = 6,371$ km (Earth radius).
  - Spatial speed: $v = \frac{d}{\Delta t}$ (km/h).
  - If a transaction occurs in New York ($40.71, -74.00$) at 14:00 and another transaction occurs on the same card in London ($51.50, -0.12$) at 14:35 ($\Delta t = 0.58$ hours):
    - Distance: $d \approx 5,585$ km.
    - Speed: $v = 5,585 / 0.58 = 9,629$ km/h.
  - Since $v > 900$ km/h, the physical speed is impossible for a human traveler, proving cloned cards, credential theft, or automated proxy relay.
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `ml/src/features/feature_extractor.py` and rule `R01_IMPOSSIBLE_TRAVEL` in `services/risk_engine/rules.py`.

---

<div style="page-break-after: always;"></div>

## 5. In-Memory State, Redis Sliding Windows & Idempotency

### Q16. How is Idempotency guaranteed in real-time payments?
- **SHORT ANSWER**: By computing a SHA-256 hash of `transaction_id` or `(customer_id + amount + timestamp)` and performing an atomic Redis `SET key "1" NX EX 86400` check before processing.
- **DEEP EXPLANATION**:
  - Network timeouts between the checkout frontend and the payment gateway often trigger automatic client retries. If the retry is processed as a new transaction, the customer is double-charged, and their 1-hour velocity count artificially doubles.
  - **Resolution**:
    1. An idempotency key is extracted from the request header or generated via `hash(customer_id, amount, timestamp)`.
    2. The API calls Redis `SET idemp:{key} 1 NX EX 86400` (Set if Not Exists with 24-hour expiration).
    3. If Redis returns `nil` (key already exists), the request is identified as a duplicate and immediately rejected or returned the cached response.
    4. At the database layer, `transaction_id` and `idempotency_key` have `UNIQUE` constraints in PostgreSQL with `ON CONFLICT DO NOTHING`.
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `services/feature_service/redis_state.py` and `tests/unit/test_redis_state.py::test_idempotency_check`.

---

<div style="page-break-after: always;"></div>

## 6. Supervised ML Modeling, Optimization & Regularization

### Q17. How does XGBoost find optimal tree splits on extreme class imbalance?
- **SHORT ANSWER**: XGBoost approximates the objective function using a second-order Taylor expansion and evaluates candidate split gains using both first-order gradients $g_i$ and second-order Hessians $h_i$ scaled by `scale_pos_weight`.
- **DEEP EXPLANATION**:
  - Objective at step $t$:
    $$\mathcal{L}^{(t)} \approx \sum_{i=1}^n \left[ g_i f_t(x_i) + \frac{1}{2} h_i f_t^2(x_i) \right] + \gamma T + \frac{1}{2}\lambda \sum_{j=1}^T w_j^2$$
    Where $g_i = \partial_{\hat{y}^{(t-1)}} l(y_i, \hat{y}^{(t-1)})$ and $h_i = \partial^2_{\hat{y}^{(t-1)}} l(y_i, \hat{y}^{(t-1)})$.
  - The optimal weight for leaf $j$ is:
    $$w_j^* = -\frac{\sum_{i \in I_j} g_i}{\sum_{i \in I_j} h_i + \lambda}$$
  - The split gain formula:
    $$\text{Gain} = \frac{1}{2}\left[ \frac{(\sum_{i \in I_L} g_i)^2}{\sum_{i \in I_L} h_i + \lambda} + \frac{(\sum_{i \in I_R} g_i)^2}{\sum_{i \in I_R} h_i + \lambda} - \frac{(\sum_{i \in I} g_i)^2}{\sum_{i \in I} h_i + \lambda} \right] - \gamma$$
  - With `scale_pos_weight = 60.5`, positive class instances have their $g_i$ and $h_i$ scaled by $60.5$, ensuring tree splits prioritize isolating rare fraud samples.
- **WHERE IT APPEARS IN THIS PROJECT**: Champion model in `ml/src/models/xgboost_model.py`.

---

<div style="page-break-after: always;"></div>

## 7. Probability Calibration, Cost Matrices & Business Decisioning

### Q18. How do you mathematically optimize decision thresholds using a financial cost model?
- **SHORT ANSWER**: We do not use an arbitrary $0.5$ probability threshold. Instead, we minimize the Expected Financial Loss function across all potential cutoffs.
- **DEEP EXPLANATION**:
  - Let $C_{\text{FN}}(x) = \text{Amount}(x) + C_{\text{chargeback_fee}}$ (Financial loss from approved fraud).
  - Let $C_{\text{FP}}(x) = C_{\text{insult}} + C_{\text{churn_risk}} \approx \$15.00$ (Loss from declining a genuine shopper).
  - Let $C_{\text{Review}} = C_{\text{analyst_wage}} \approx \$3.50$ (Cost of manual forensic review).
  - For a transaction with calibrated fraud probability $p = P(\text{Fraud}|x)$:
    - Expected Cost of Auto-Approve: $E[\text{Approve}] = p \cdot C_{\text{FN}}(x)$
    - Expected Cost of Auto-Block: $E[\text{Block}] = (1 - p) \cdot C_{\text{FP}}$
    - Expected Cost of Manual Review: $E[\text{Review}] = C_{\text{Review}} + p \cdot (\text{Review Error FN}) + (1 - p) \cdot (\text{Review Error FP})$
  - The decision rule chooses the action with the lowest expected cost:
    $$\text{Decision}^* = \arg\min \{E[\text{Approve}], E[\text{Review}], E[\text{Block}]\}$$
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `services/risk_engine/cost_model.py` and `tests/unit/test_risk_engine.py::test_financial_cost_model`.

---

<div style="page-break-after: always;"></div>

## 8. Multi-Factor Risk Engine & Rule Policies

### Q19. What is the Multi-Factor Risk Score formula and how does it arbitrate decisions?
- **SHORT ANSWER**: A 0–100 composite index combining calibrated ML probability ($55\%$), unsupervised anomaly score ($15\%$), behavioral volatility ($15\%$), and deterministic rule penalties ($15\%$).
- **DEEP EXPLANATION**:
  - Formula:
    $$\text{Score} = 100 \times \min\left(1.0, \, 0.55 P_{\text{ML}} + 0.15 S_{\text{anom}} + 0.15 S_{\text{behav}} + 0.15 S_{\text{rules}}\right)$$
  - **Tiers & Action Matrix**:
    - **Score $< 30$ $\implies$ APPROVE**: Sub-60ms fast-path authorization.
    - **Score $30 - 74$ $\implies$ REVIEW**: Step-up 3D-Secure 2.0 MFA challenge or queued for fraud analyst forensic inspection.
    - **Score $\ge 75$ $\implies$ BLOCK**: Immediate decline with adverse action security code.
  - **Deterministic Rule Overrides**: Regardless of ML output, hard security rules trigger immediate escalation:
    - `R01_IMPOSSIBLE_TRAVEL` ($v > 900$ km/h): Severity = HIGH ($+40$ points).
    - `R02_VELOCITY_BURST_1M` ($\ge 3$ txns in 60s): Severity = CRITICAL ($+50$ points).
    - `R05_DEVICE_SHARING_ANOMALY` ($\ge 4$ accounts on one device in 24h): Severity = CRITICAL ($+50$ points).
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `services/risk_engine/engine.py` and `services/risk_engine/rules.py`.

---

<div style="page-break-after: always;"></div>

## 9. Observability, Drift & MLOps

### Q20. How is Population Stability Index (PSI) calculated to detect Data Drift in production?
- **SHORT ANSWER**: PSI measures the divergence between baseline reference feature distributions and live production inference distributions across quantiles. $\text{PSI} > 0.25$ indicates significant drift requiring retraining.
- **DEEP EXPLANATION**:
  - Training features are partitioned into $B=10$ quantile bins.
  - For each bin $b$:
    $$\text{PSI} = \sum_{b=1}^B \left( \text{Actual}_b - \text{Expected}_b \right) \times \ln\left( \frac{\text{Actual}_b}{\text{Expected}_b} \right)$$
    Where $\text{Expected}_b$ is the proportion in bin $b$ during offline training, and $\text{Actual}_b$ is the observed proportion in live production over a 7-day sliding window.
  - **Interpretation Standards**:
    - $\text{PSI} < 0.10$: No significant change; model is stable.
    - $0.10 \le \text{PSI} \le 0.25$: Moderate drift; warning triggered, schedule retraining.
    - $\text{PSI} > 0.25$: Severe distribution shift; trigger automated alerting and evaluate Champion-Challenger promotion.
- **WHERE IT APPEARS IN THIS PROJECT**: Implemented in `ml/src/monitoring/drift_detector.py`, verified in `tests/unit/test_drift.py`, and visualized in Grafana.

---

<div style="page-break-after: always;"></div>

## 10. Empirical Benchmarks, Scaling to 50k TPS & Technical Trade-offs

### Q21. What empirical latencies did this project achieve in benchmark testing?
- **SHORT ANSWER**: Benchmarked across 250 live simulated payment transactions: Feature enrichment p50 = 16.07 ms (p95 = 32.04 ms); ML Inference + TreeSHAP p50 = 29.86 ms (p95 = 39.88 ms); Risk Arbitration p50 = 0.07 ms (p95 = 0.10 ms); Total HTTP roundtrip p50 = 65.59 ms (p95 = 92.24 ms) with a 100% success rate.
- **DEEP EXPLANATION**:
  - Latency breakdown per subsystem:
    1. *FastAPI serialization & Pydantic validation*: $\approx 1.8$ ms
    2. *Redis State query & kinematic feature calculation*: $\approx 16.0$ ms (p95 = $32.0$ ms)
    3. *XGBoost inference*: $\approx 4.2$ ms
    4. *Isotonic calibration*: $\approx 0.3$ ms
    5. *Isolation Forest anomaly scoring*: $\approx 0.4$ ms
    6. *TreeSHAP attribution calculation*: $\approx 25.0$ ms
    7. *Multi-factor risk arbitration & rule evaluation*: $\approx 0.07$ ms
    8. *PostgreSQL asynchronous persistence*: $\approx 3.5$ ms (off critical path)
  - Meets the strict sub-100ms financial authorization requirement.
- **WHERE IT APPEARS IN THIS PROJECT**: Benchmark harness in `benchmarks/latency_benchmark.py` and documented in `docs/BENCHMARK_REPORT.md`.

---

### Q22. How would you scale this architecture to 50,000 TPS (Visa Enterprise Scale)?
- **SHORT ANSWER**: Horizontally partition Kafka into 128+ partitions by customer hash, migrate Redis to a clustered Redis Enterprise / Aerospike cluster, serve XGBoost models via NVIDIA Triton / ONNX Runtime with dynamic micro-batching, and replace PostgreSQL with distributed ScyllaDB/Cassandra.
- **DEEP EXPLANATION**:
  1. **Kafka Topic Sharding**: A single Kafka partition handles $\approx 1,500 - 3,000$ TPS. Scaling to 50k TPS requires $32 - 64$ partitions per topic with identical key hashing on `customer_id`.
  2. **In-Memory State Tier**: Single Redis instances top out at $\approx 80\text{k}$ operations/sec. At 50k TPS (requiring $3 - 5$ ops per transaction = 200k ops/sec), we deploy a multi-node Redis Cluster with consistent hashing or transition to Aerospike Hybrid Memory Architecture (RAM index + NVMe SSD data).
  3. **Compiled Model Serving via Triton / ONNX**: Pure Python worker loops have GIL bottlenecks under 50k TPS. We compile the XGBoost ensemble into an ONNX computational graph served via NVIDIA Triton Model Server using C++ gRPC endpoints, achieving sub-2ms batch scoring.
  4. **Distributed Commit Log for Storage**: Replace single-instance PostgreSQL with ScyllaDB (C++ Cassandra rewrite), providing distributed linear write scalability across nodes.
- **WHERE IT APPEARS IN THIS PROJECT**: Production scaling blueprint documented in `docs/DEPLOYMENT.md` Section 4.

---

### Q23. What were the most challenging bugs or trade-offs you solved in this project?
- **SHORT ANSWER**:
  1. *TreeSHAP latency overhead on the real-time path*: Resolved by extracting background reference subsets ($N=50$) to bound tree traversal time to $< 30$ ms.
  2. *Vite SPA asset routing under subpath mounting*: Resolved by configuring `base: './'` in `vite.config.js` and dynamic API port switching for `/dashboard`.
  3. *Zero-leakage race conditions in state updates*: Resolved by strictly separating the read phase (pre-decision feature enrichment) from the write phase (post-decision state commit in Redis).
  4. *Connection timeout hangs during unit testing*: Resolved by adding non-blocking microsecond TCP socket probes before attempting Kafka/Redis client connections when running in offline testing mode.
- **DEEP EXPLANATION**:
  - Sharing concrete engineering war stories demonstrates authentic hands-on senior engineering capability rather than theoretical book knowledge.

---

<div style="page-break-after: always;"></div>

## Summary Cheat Sheet for Interview Day

| Question Category | Key Terminology & Formula to Mention | Code File Reference |
| :--- | :--- | :--- |
| **Why Kafka?** | Partition key serialization, disk pagecache buffer, consumer group offset replayability | `services/streaming_client.py` |
| **Why XGBoost?** | Tabular inductive bias, second-order Taylor expansion ($g_i, h_i$), `scale_pos_weight`, $< 8$ ms C++ scoring | `ml/src/models/xgboost_model.py` |
| **Why Redis?** | $O(\log N + M)$ `ZSET` sliding windows, RAM reads $< 1$ ms vs Postgres disk lock contention | `services/feature_service/redis_state.py` |
| **Why Isotonic?** | Non-parametric monotonic step calibration, avoids Platt sigmoid rigidness, ECE = 0.0014 | `ml/src/calibration/calibrator.py` |
| **Why Isolation Forest?** | Linear time $O(n \cdot t \cdot \psi)$, random tree depth $h(x)$, zero-day attack triangulation | `ml/src/anomaly/isolation_forest.py` |
| **Why TreeSHAP?** | Cooperative game theory axioms (Efficiency, Symmetry, Dummy, Additivity), $O(TLD^2)$ polynomial time | `services/inference_service/consumer.py` |
| **Why Decoupled Risk Engine?** | Business agility, compliance mandates (OFAC/AML), dynamic Black Friday threshold tuning | `services/risk_engine/engine.py` |
| **Zero Data Leakage?** | Chronological train/val/test splits, Redis state updated strictly *after* risk decisioning | `tests/unit/test_features.py` |
| **Cold-Start Handling?** | Bayesian shrinkage: $\hat{\mu} = \frac{N}{N+K}\bar{x} + \frac{K}{N+K}\mu_{\text{global}}$ ($K=5$) | `services/risk_engine/entity_resolution.py` |
| **Real-Time Kinematics?** | Haversine distance, commercial aviation threshold ($v > 900$ km/h = Impossible Travel) | `services/risk_engine/rules.py` |
| **Production SLA?** | Total roundtrip p50 = 65.59 ms, p95 = 92.24 ms across 250 live transactions | `benchmarks/latency_benchmark.py` |
