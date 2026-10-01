# CLAUDE.md - Instructions for Claude Agent

This file provides system context and operational guidelines for Claude-based coding agents working within this repository.

## 1. Project Overview
The **Real-Time Payment Fraud Detection & Risk Engine** is an end-to-end, production-grade fraud prevention pipeline.
It demonstrates real-time feature enrichment (Kafka, Redis), machine learning inference (Logistic Regression, Random Forest, XGBoost), probability calibration (Isotonic/Platt), behavioral anomaly detection (Isolation Forest), rule engine heuristics, multi-factor risk scoring (0–100 scale), decisioning (`APPROVE`, `REVIEW`, `BLOCK`), and SHAP explainability.

## 2. Core Operational Commandments
1. **Document-Driven Development**: Consult `docs/` before making architectural or code modifications.
2. **Preserve Truthfulness**: Do not fabricate model benchmarks, evaluation metrics, SHAP contributions, or streaming statistics. Measure all values.
3. **Temporal Leakage Prevention**: Never compute customer historical features using future transactions. Split datasets strictly by time.
4. **Data Privacy**: No real credit card numbers, CVVs, or PII. Use synthetic identifiers (`CUST-XXXX`, `MERCH-XXXX`, `TXN-XXXX`).
5. **Architectural Coherence**: Maintain clean separation between ML inference, anomaly scoring, deterministic rules, and final risk arbitration in the Risk Engine.
6. **Testing**: Write and run unit/integration tests with `pytest` for every new component.
7. **Keep Documentation Synchronized**: When altering endpoints, schemas, or features, update the corresponding file in `docs/` and log entries in `docs/DECISIONS.md`.
