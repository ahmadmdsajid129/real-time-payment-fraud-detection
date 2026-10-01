# Contributing Guidelines

Thank you for contributing to the **Real-Time Payment Fraud Detection & Risk Engine** project.
To maintain high engineering and machine learning standards, follow this guide for branching, commits, testing, and documentation.

---

## 1. Development Principles
- **No Data Leakage**: Any feature computation logic touching timestamped data must be chronologically sound.
- **Spec-First**: Code changes that alter APIs, database tables, or model inputs must first be updated in `docs/` and tracked in `docs/DECISIONS.md`.
- **Reproducibility**: Experiments must be seeded and run via scripts in `ml/` with outputs recorded in `docs/EXPERIMENTS.md`.
- **Honest Metrics**: Never invent numbers. Benchmark numbers must be reproducible via `pytest` or evaluation scripts.

---

## 2. Local Environment Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- Docker & Docker Compose
- Git

### Quick Setup
1. Clone the repository and navigate to root:
   ```bash
   git clone <repo-url>
   cd "real-time-payment and fraud detection"
   ```
2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
3. Set up Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r ml/requirements.txt
   ```
4. Start core backing services (PostgreSQL, Redis, Kafka):
   ```bash
   docker compose up -d postgres redis kafka zookeeper
   ```

---

## 3. Branching & Commit Conventions

### Branch Naming
- `feature/<phase-name>` (e.g., `feature/phase1-eda`, `feature/phase9-risk-engine`)
- `fix/<issue-name>`
- `docs/<doc-update>`

### Commit Messages
Follow Conventional Commits:
- `feat(ml): implement calibrated isotonic regression wrapper`
- `feat(risk): add velocity attack rule to decision engine`
- `fix(features): prevent future leakage in rolling average calculation`
- `docs(api): update OpenAPI spec for /transactions/score`
- `test(e2e): add idempotency deduplication integration test`

---

## 4. Testing & Code Quality Expectations
Before pushing or submitting PRs:
1. Run all unit and integration tests:
   ```bash
   pytest tests/unit tests/integration -v
   ```
2. Check formatting and linting:
   ```bash
   ruff check .
   black --check .
   ```
3. Verify documentation synchronization:
   - If schemas changed, update `docs/DATABASE.md`.
   - If endpoints changed, update `docs/API.md`.
   - If model parameters or features changed, update `docs/MODEL_CARD.md` or `docs/FEATURE_ENGINEERING.md`.
