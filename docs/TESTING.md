# Testing Strategy & Quality Assurance Specification

---

## 1. Multi-Tier Testing Pyramid

Testing in this repository ensures mathematical correctness, temporal data integrity, and distributed resilience:

```text
                  ┌──────────────────────┐
                  │     E2E Scenarios    │  <-- Full Pipeline (Kafka In -> Decision In DB)
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │   Integration Tests  │  <-- Redis State, PostgreSQL Migrations, FastAPI
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   ┌───────────────────┐             ┌───────────────────┐
   │ ML & Feature Tests│             │  Unit & Rule Tests│
   │ - Leakage Checks  │             │ - Risk Engine     │
   │ - Calibration Bounds            │ - Rule Logic      │
   │ - Deterministic Output          │ - Pydantic Schemas│
   └───────────────────┘             └───────────────────┘
```

---

## 2. Test Suite Directory Structure

```text
tests/
├── unit/
│   ├── test_rules.py            # Rule engine triggers (velocity, travel, device)
│   ├── test_risk_engine.py      # Multi-factor formula, weights, 0-100 bounds
│   ├── test_features.py         # Feature calculations and zero-leakage math
│   └── test_schemas.py          # Pydantic serialization and validation
├── integration/
│   ├── test_redis_state.py      # Rolling sliding window ZSETs and expiry
│   ├── test_postgres_repo.py    # Transaction, prediction, and decision inserts
│   ├── test_idempotency.py      # Duplicate event handling and deduplication
│   └── test_api_endpoints.py    # FastAPI HTTP endpoints and error handling
├── ml/
│   ├── test_temporal_leakage.py # Asserts feature matrices contain no lookahead
│   ├── test_model_inference.py  # Model prediction consistency and shapes
│   └── test_calibration.py      # Asserts calibrated probs lie in [0, 1]
└── e2e/
    └── test_streaming_e2e.py    # Ingests event into Kafka and asserts Postgres decision
```

---

## 3. Critical Test Invariants & Assertions

### 3.1 Risk Score Invariant
```python
def test_risk_score_bounds():
    """Guarantee risk score is strictly bounded in [0.0, 100.0] under extreme inputs."""
    engine = RiskEngine()
    for ml_prob in [0.0, 0.5, 1.0, 1.5]: # test clipping
        for anom in [0.0, 1.0]:
            for rules in [0.0, 5.0]:
                score, decision = engine.evaluate(
                    calibrated_prob=ml_prob,
                    anomaly_score=anom,
                    behavioral_score=1.0,
                    rule_score=rules
                )
                assert 0.0 <= score <= 100.0
                assert decision in ["APPROVE", "REVIEW", "BLOCK"]
```

### 3.2 Temporal Feature Leakage Assertion
```python
def test_no_future_leakage_in_aggregations():
    """Verify that a customer's rolling 1h spend excludes the current transaction."""
    t0 = datetime(2026, 10, 1, 10, 0, 0)
    txns = [
        {"amount": 100.0, "timestamp": t0},
        {"amount": 500.0, "timestamp": t0 + timedelta(minutes=15)},
    ]
    # Current transaction at minute 30 with amount 1000
    current_txn = {"amount": 1000.0, "timestamp": t0 + timedelta(minutes=30)}
    
    features = calculate_historical_features(customer_history=txns, current=current_txn)
    # Average must be (100 + 500) / 2 = 300, NOT (100 + 500 + 1000) / 3
    assert features["customer_avg_amount"] == 300.0
```

### 3.3 Idempotency Invariant
```python
def test_duplicate_transaction_idempotency():
    """Re-submitting the same transaction ID must return cached decision without duplicating records."""
    txn = create_sample_transaction(txn_id="TXN-IDEMP-001")
    res1 = client.post("/api/v1/transactions/score", json=txn)
    res2 = client.post("/api/v1/transactions/score", json=txn)
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["decision"] == res2.json()["decision"]
    # Check that database has exactly 1 record for TXN-IDEMP-001
```

---

## 4. Running the Test Suites

### Execute All Fast Unit Tests
```bash
pytest tests/unit -v
```

### Execute Feature & ML Tests
```bash
pytest tests/ml -v
```

### Execute Integration Tests (Requires Running Backing Services)
```bash
docker compose up -d postgres redis
pytest tests/integration -v
```

### Coverage Report
```bash
pytest --cov=services --cov=ml tests/
```
Target: $\ge 85\%$ test coverage across critical risk and feature evaluation logic.
