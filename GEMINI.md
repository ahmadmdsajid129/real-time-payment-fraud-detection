# GEMINI.md - Instructions for Gemini / Antigravity Agent

This file outlines operational directives for Google DeepMind Gemini / Antigravity instances working on the **Real-Time Payment Fraud Detection & Risk Engine**.

## 1. Operating Context & Framework
- **Workspace**: `e:/real-time-payment and fraud detection`
- **Shell**: PowerShell (Windows OS)
- **Primary Tooling**: Python 3.11+, Scikit-learn, XGBoost, SHAP, Redis, Kafka, PostgreSQL, FastAPI, Next.js / TypeScript.
- **Reference Skills**: Use `antigravity-guide` or `agy-customizations` if internal IDE customizations are required.

## 2. Core Constraints
1. **Spec-First Enforcement**: Always verify `PRD.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE.md`, and `docs/API.md` before generating code.
2. **Never Fabricate Numbers**: Never generate fake confusion matrices, metrics, or SHAP contributions. Compute them from actual test evaluation sets.
3. **No Temporal Data Leakage**:
   - Time-series splits must strictly observe timestamp boundaries (Train $\le t_1 <$ Val $\le t_2 <$ Test).
   - In feature calculation, behavioral aggregations (e.g., historical rolling average amount) must strictly exclude the current transaction timestamp.
4. **Idempotency & State Integrity**:
   - Deduplicate transactions using an idempotency key (hash of `transaction_id` or `customer_id` + `timestamp` + `amount`).
   - Redis stores rolling sliding-window state (counts, sums, sets).
   - PostgreSQL stores durable transaction histories, calibrated probabilities, risk scores, and review outcomes.
5. **No Synthetic CVVs / Real Card Numbers**: Use synthetic identifiers (`CUST-XXXX`, `MERCH-XXXX`, `TXN-XXXX`, masked tokens).

## 3. Communication & Verification Protocol
- At the conclusion of every implementation phase, verify test runs (`pytest`), check outputs, and update documentation (`CHANGELOG.md`, `docs/DECISIONS.md`).
- When creating markdown artifacts or reports, adhere to formatting rules (clear headers, code blocks with languages, clickable links).
