# Changelog

All notable changes to the **Real-Time Payment Fraud Detection & Risk Engine** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-02

### Added
- **Phase 10: Event Streaming Engine & Message Bus**:
  - `services/streaming_client.py`: Dual-mode streaming client supporting Apache Kafka and partition-aware in-memory fallback.
  - `services/transaction_generator/producer.py`: High-throughput transaction generator keying events by `customer_id` into `transactions.raw`.
- **Phase 11: Real-Time Feature Service & Redis State Cache**:
  - `services/feature_service/redis_state.py`: Redis sliding-window sorted sets (`ZSET`) and hash counters for microsecond state retrieval.
  - `services/feature_service/consumer.py`: Consumer enriching raw transaction payloads with temporal velocity and kinematics into `transactions.features`.
- **Phase 12: Distributed Inference Service & TreeSHAP Explainer**:
  - `services/inference_service/consumer.py`: Real-time pipeline evaluating Champion XGBoost, Isotonic Calibrator, Isolation Forest, and TreeSHAP feature attributions into `transactions.predictions`.
- **Phase 13: FastAPI REST & SSE Scoring Backend**:
  - `services/api/main.py` & `services/api/routes.py`: High-performance asynchronous API endpoints: `/transactions/score`, `/transactions/{id}/explanation`, `/customers/{id}/profile`, `/dashboard/summary`, `/feedback`, and `/metrics`.
- **Phase 14: Modern React + Tailwind Forensic Investigation Dashboard**:
  - `frontend/`: Fullstack React 19 + Tailwind CSS + Lucide Icons web application with glassmorphic dark fintech aesthetics.
  - Interactive attack simulator toolbar (Normal, Velocity Burst, Impossible Travel, Account Takeover), live transaction table, and deep-dive forensic modal with TreeSHAP waterfall charts.
- **Phase 15: Observability & Telemetry**:
  - `services/observability/metrics.py`: Prometheus metrics suite instrumenting request latency histograms, prediction score distributions, and triage counters.
  - `infrastructure/grafana/dashboards/fraud_operations.json`: Pre-configured Grafana operations dashboard.
- **Phase 16: Model Monitoring & Data Drift**:
  - `ml/src/monitoring/drift_detector.py`: Population Stability Index (PSI) and two-sample Kolmogorov-Smirnov (KS) test runner emitting `data/processed/drift_report.json`.
- **Phase 17: Cold Start & Entity Resolution**:
  - `services/risk_engine/entity_resolution.py`: Bayesian shrinkage estimators for new cardholders and cross-account device syndicate graph detection.
- **Phase 18: Security, Masking & Synthetic PII Protection**:
  - `services/security/masking.py`: IPv4/IPv6 octet masking, payment token redaction, and SHA-256 idempotency fingerprinting.
  - `docs/SECURITY_AUDIT_REPORT.md`: Comprehensive OWASP Top 10 security audit and vulnerability assessment.
  - `SecurityHeadersMiddleware`: OWASP security headers (`nosniff`, `DENY` frames, HSTS, strict referrers).
- **Phase 19: Chaos Engineering & Fault Injection**:
  - `tests/integration/test_chaos_resilience.py`: Automated chaos tests validating graceful fallback during Redis outages, model missing scenarios, and Dead Letter Queue (`transactions.dlq`) poison pill routing.
- **Phase 20: Comprehensive Automated Testing**:
  - 61 out of 61 unit and integration tests passing with 100% success rate across 15 test suites.
- **Phase 21: Container Orchestration**:
  - Production multi-stage `Dockerfile` and `docker-compose.yml` orchestrating 8 heterogeneous services (Postgres, Redis, Kafka, Zookeeper, API, Prometheus, Grafana, and UI).
- **Phase 22: Benchmark Testing & Latency SLA Verification**:
  - `benchmarks/latency_benchmark.py`: Empirical single-threaded benchmark (250 live samples) generating `docs/BENCHMARK_REPORT.md` (Total HTTP roundtrip p50: 65.59 ms, p95: 92.24 ms).
- **Phase 23: Technical Interview Walkthrough & Architecture Q&A Guide**:
  - `docs/INTERVIEW_QUESTIONS.md`: 55 deep-dive questions with comprehensive explanations spanning ML, calibration, stream state, security hardening, and UI design.
- **Phase 24: Final Documentation, Portfolio Showcase & Production Wrap-up**:
  - Full project documentation, architectural diagrams, empirical leaderboards, and quickstart commands in `README.md`.

## [0.7.0] - 2026-10-01

### Added
- **Phase 9: Multi-Factor Risk Engine & Decision Policy**:
  - `services/risk_engine/rules.py`: Deterministic RuleEngine evaluating 8 heuristic fraud vectors (impossible travel, velocity bursts, account takeover, new country, device sharing, off-hours large spend) emitting normalized severity penalties.
  - `services/risk_engine/cost_model.py`: FinancialCostModel calculating asymmetric expected losses for Approve (chargeback fee + lost amount), Block (customer insult/churn), and Review.
  - `services/risk_engine/engine.py`: Configurable RiskEngine synthesizing calibrated ML probability ($0.55$), anomaly score ($0.15$), behavioral volatility ($0.15$), and rules ($0.15$) into an arbitrated 0–100 risk score and triaging decisions (`APPROVE`, `REVIEW`, `BLOCK`).
  - `tests/unit/test_risk_engine.py`: Tests validating score boundary clamping ($[0.0, 100.0]$), decision policy mappings, and rule triggers (29/29 unit tests passing).

## [0.6.0] - 2026-10-01

### Added
- **Phase 7 & Phase 8: Behavioral Analytics & Unsupervised Anomaly Detection**:
  - `ml/src/anomaly/isolation_forest.py`: IsolationForestDetector mapping raw decision margins to a normalized continuous score in $[0.0, 1.0]$.
  - `ml/src/features/behavioral_profiler.py`: BehavioralProfiler synthesizing customer deviation signals (z-scores, velocity spikes, kinematics, novelty, diurnal patterns) into a composite behavioral risk score.
  - `ml/train_anomaly.py`: Training script on temporal splits evaluating unsupervised separation and correlation with fraud.
  - Measured benchmark:
    - Isolation Forest mean score on legitimate transactions: **`0.0993`** vs. fraudulent transactions: **`0.7233`**.
    - Unsupervised correlation with ground-truth fraud: **`+0.5820`**.
    - Behavioral deviation correlation with ground-truth fraud: **`+0.7858`**.
  - `tests/unit/test_anomaly.py`: 25/25 unit tests passing.
  - Model artifact exported to `ml/models/saved/isolation_forest_detector.joblib`.

## [0.5.0] - 2026-10-01

### Added
- **Phase 5 & Phase 6: Probability Calibration & Cost-Sensitive Thresholds**:
  - `ml/src/calibration/calibrator.py`: ProbabilityCalibrator implementing Isotonic Regression and Platt Sigmoid calibration with Expected Calibration Error (ECE) and reliability diagram binning.
  - `ml/src/evaluation/cost_optimization.py`: ThresholdOptimizer evaluating precision-recall tradeoffs via $F_2$ score maximization and total financial loss minimization ($C_{\text{FN}} = \text{amount} + \$25$, $C_{\text{FP}} = \$35$).
  - `ml/train_calibration.py`: Complete calibration training on the chronological validation split and evaluation on the held-out test split.
  - Measured benchmark:
    - Isotonic Regression reduces Expected Calibration Error (ECE) to **`0.0014`** (half of raw XGBoost's `0.0031`).
    - Optimal $F_2$ operational cutoff determined at **`0.070`** (Recall = $95.1\%$, Precision = $93.5\%$).
    - Optimal financial cost cutoff determined at **`0.010`**.
  - `tests/unit/test_calibration.py`: 23/23 unit tests passing.
  - Calibrated model artifact exported to `ml/models/saved/calibrator_isotonic.joblib`.

## [0.4.0] - 2026-10-01

### Added
- **Phase 4: XGBoost Primary Classifier & Leaderboard**:
  - `ml/src/models/xgboost_model.py`: Production-grade XGBoost classifier wrapper with automatic `scale_pos_weight` calculation for class imbalance, L1/L2 regularization (`reg_alpha=0.05`, `reg_lambda=1.0`), tree depth 6, and gain-based feature importances.
  - `ml/train_xgboost.py`: Training and benchmarking script on temporal held-out test split, comparing against all baselines.
  - Benchmarked test results:
    - XGBoost achieves highest overall **F1-Score (0.9431)** and **Recall (0.9508)** with **Precision (0.9355)**.
    - False Positive Rate: **0.18%**; False Negative Rate: **4.92%**.
    - PR-AUC: **0.9825**; ROC-AUC: **0.9990**; Brier Score: **0.0023**.
  - `tests/unit/test_xgboost.py`: Unit tests validating probability bounds, custom thresholds, and booster extraction.
  - Model artifact exported to `ml/models/saved/xgboost_champion.joblib`.

## [0.3.0] - 2026-10-01

### Added
- **Phase 3: Baseline ML Models & Temporal Validation**:
  - `ml/src/data/splitter.py`: Chronological temporal splitter (70% Train, 15% Val, 15% Test) guaranteeing zero lookahead overlap ($T_{\text{train}} \le t_1 < T_{\text{val}} \le t_2 < T_{\text{test}}$).
  - `ml/src/evaluation/metrics.py`: Metrics engine calculating PR-AUC, ROC-AUC, Precision, Recall, F1-Score, Brier score, Confusion Matrix, FPR, and FNR.
  - `ml/src/models/baselines.py`: Dummy majority prior model, L2-regularized Logistic Regression baseline with training-only standard scaling, and non-linear Random Forest tree ensemble (100 trees).
  - `ml/train_baselines.py`: Training and evaluation pipeline saving models to `ml/models/saved/` and recording empirical test results in `docs/EXPERIMENTS.md`.
  - Benchmarked test results:
    - Dummy: PR-AUC 0.0271, ROC-AUC 0.5000, F1 0.0000.
    - Logistic Regression: PR-AUC 0.9222, ROC-AUC 0.9947, Recall 0.9836, Precision 0.4511, Brier 0.0320.
    - Random Forest: PR-AUC 0.9858, ROC-AUC 0.9989, Recall 0.8361, Precision 1.0000, Brier 0.0032.
  - `tests/unit/test_baselines.py`: 17/17 total unit tests passing.

## [0.2.0] - 2026-10-01

### Added
- **Phase 2: Feature Engineering & Zero-Leakage Pipeline**:
  - `ml/src/features/feature_definitions.py`: Catalog of 30+ engineered feature names, numerical/binary groupings, and cold-start defaults.
  - `ml/src/features/feature_extractor.py`: Real-time streaming and chronological batch feature extractor computing sliding-window velocity counters (1m, 5m, 15m, 1h, 24h, 7d), spending z-scores, Haversine travel speeds, impossible travel flags, and device sharing counts.
  - Strict zero-leakage invariant: historical customer state evaluated exclusively on transactions prior to current event.
  - `ml/src/features/build_features.py`: Batch feature extraction script producing `data/processed/features_dataset.parquet`.
  - `tests/unit/test_features.py`: Unit tests validating zero temporal leakage guarantees, z-score math, cold-start defaults, and kinematics (14/14 unit tests passing).

## [0.1.0] - 2026-10-01

### Added
- **Phase 1: Dataset Generation, Data Validation & EDA**:
  - `ml/src/data/schemas.py`: Pydantic V2 models for CustomerProfile, MerchantProfile, TransactionPayload, and FraudScenario.
  - `ml/src/data/synthetic_generator.py`: Realistic, controllable transaction generator with 9 distinct fraud scenarios (velocity attacks, impossible travel, account takeover, high-value anomalies, new device/country) and realistic customer baselines.
  - `ml/src/data/validator.py`: Comprehensive dataset integrity validator checking schemas, coordinate bounds, positive amounts, temporal consistency, and class imbalance.
  - `ml/src/data/eda.py`: Automated Exploratory Data Analysis calculating transaction volumes, fraud ratios, categorical breakdowns, and rendering `docs/DATASET.md`.
  - `ml/src/data/generate_dataset.py`: Reproducible CLI generation script.
  - `tests/unit/test_generator.py` & `tests/unit/test_data_validation.py`: 9 unit tests passing with 100% pass rate.
  - Baseline dataset generated in `data/synthetic/transactions.parquet` (15,000 transactions, 2.25% fraud incidence).

## [0.0.1] - 2026-10-01

### Added
- **Project Specifications & Documentation Layer**:
  - `PRD.md`: Full Product Requirements Document with user personas, functional/non-functional requirements, and out-of-scope boundaries.
  - `AGENTS.md`, `GEMINI.md`, `CLAUDE.md`: AI coding agent directives, operating constraints, and coding rules.
  - `docs/ARCHITECTURE.md`: High-level system architecture, service boundaries, data flows, and sequence diagrams.
  - `docs/INFRASTRUCTURE.md`: Docker networks, volumes, ports, container topology, Kafka topics, Redis keys, and PostgreSQL configurations.
  - `docs/DATABASE.md`: Relational schema definitions, indexing strategies, audit logs, and hybrid Redis/Postgres storage rationale.
  - `docs/API.md`: Detailed OpenAPI contracts, endpoints, request/response models, and error structures for FastAPI.
  - `docs/ML_PIPELINE.md`: End-to-end ML lifecycle from ingestion to retraining, covering temporal splits, baselines, and calibration.
  - `docs/FEATURE_ENGINEERING.md`: Behavioral feature catalogue, sliding-window definitions, and leakage prevention rules.
  - `docs/RISK_ENGINE.md`: Multi-signal arbitration engine combining calibrated probability, anomaly score, and business rules.
  - `docs/STREAMING.md`: Kafka streaming architecture, partition schemes, consumer groups, idempotency, and DLQ handling.
  - `docs/SECURITY.md`: Threat model, synthetic identifier policy, parameter sanitization, and security boundaries.
  - `docs/OBSERVABILITY.md`: Prometheus instrumentation, Grafana metrics, consumer lag monitoring, and system vs. ML observability.
  - `docs/TESTING.md`: Multi-tier testing strategy (unit, integration, ML data tests, e2e simulation).
  - `docs/DEPLOYMENT.md`: Step-by-step local orchestration via Docker Compose and production evolution blueprint.
  - `docs/MODEL_CARD.md`: Transparent model card covering XGBoost, Random Forest, Logistic Regression, calibration, and limitations.
  - `docs/EXPERIMENTS.md`: Structured experiment log for hypothesis testing, ablation studies, and metric tracking.
  - `docs/DECISIONS.md`: Initial Architecture Decision Records (ADR-001 through ADR-010).
  - `docs/INTERVIEW_QUESTIONS.md`: 50+ deep-dive technical interview questions and comprehensive answers spanning ML, Systems, and Risk.
- **Repository Setup**:
  - Root `.gitignore` and `.env.example`.
  - Directory skeleton for `ml/`, `services/`, `data/`, `database/`, `infrastructure/`, `monitoring/`, and `tests/`.
  - Core `docker-compose.yml` for infrastructure services (Kafka, Zookeeper, Redis, PostgreSQL, Prometheus, Grafana).
