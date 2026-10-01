# Changelog

All notable changes to the **Real-Time Payment Fraud Detection & Risk Engine** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

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
