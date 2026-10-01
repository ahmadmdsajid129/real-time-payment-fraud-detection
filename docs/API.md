# FastAPI REST Interface Specification

---

## 1. Overview & Protocol Standards
All endpoints are exposed under `/api/v1` by the FastAPI backend service (`http://localhost:8000`).
- **Data Exchange**: JSON (`application/json`)
- **Authentication**: Stateless Bearer token (`Authorization: Bearer <token>`) simulated in staging. For local portfolio inspection, endpoints accept requests with standard simulated developer tokens or unauthenticated development mode.
- **Error Format**: RFC 7807 compliant problem details (`{"type": "...", "title": "...", "status": 400, "detail": "...", "instance": "..."}`).

---

## 2. API Endpoint Directory

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service liveness, readiness, and backing dependencies status. |
| `GET` | `/metrics` | Prometheus metrics scrape target. |
| `POST` | `/api/v1/transactions/score` | Synchronously evaluates a single payment transaction. |
| `GET` | `/api/v1/transactions/{transaction_id}` | Retrieves full stored payload, features, and decision for an ID. |
| `GET` | `/api/v1/transactions/{transaction_id}/explanation` | Retrieves SHAP feature contributions and explanation waterfall. |
| `GET` | `/api/v1/customers/{customer_id}/profile` | Retrieves customer behavioral baseline, known devices, and recent velocity. |
| `GET` | `/api/v1/risk/{transaction_id}` | Retrieves detailed risk breakdown, rule evaluations, and cost model. |
| `GET` | `/api/v1/models` | Lists model registry versions, champion/challengers, and benchmark metrics. |
| `GET` | `/api/v1/dashboard/summary` | Real-time aggregate KPIs (throughput, fraud rate, approve/review/block counts). |
| `GET` | `/api/v1/dashboard/recent-transactions` | Recent evaluated transactions stream for live monitor table. |
| `GET` | `/api/v1/dashboard/risk-distribution` | Histogram buckets of risk scores (0–100). |
| `GET` | `/api/v1/dashboard/fraud-trends` | Time-series data points of fraud volume vs. genuine volume. |
| `POST`| `/api/v1/feedback` | Submits analyst feedback/dispute label for a transaction. |

---

## 3. Detailed Endpoint Contracts

### 3.1 `GET /api/v1/health`
Checks health of PostgreSQL, Redis, and active ML models.
```json
// Response: 200 OK
{
  "status": "HEALTHY",
  "version": "1.0.0",
  "timestamp": "2026-10-01T12:00:00Z",
  "dependencies": {
    "postgres": "UP",
    "redis": "UP",
    "kafka": "UP",
    "champion_model_loaded": true
  }
}
```

---

### 3.2 `POST /api/v1/transactions/score`
Synchronously scores an incoming transaction.
```json
// Request Body:
{
  "transaction_id": "TXN-8839210",
  "timestamp": "2026-10-01T12:15:30Z",
  "customer_id": "CUST-10492",
  "merchant_id": "MERCH-4091",
  "amount": 45000.00,
  "currency": "INR",
  "country": "SG",
  "city": "Singapore",
  "device_id": "DEV-NEW-8812",
  "payment_method": "CREDIT_CARD",
  "ip_address": "103.252.112.4"
}
```
```json
// Response: 200 OK
{
  "transaction_id": "TXN-8839210",
  "risk_score": 89.4,
  "decision": "BLOCK",
  "calibrated_fraud_probability": 0.865,
  "anomaly_score": 0.78,
  "behavioral_risk_score": 0.91,
  "model_version": "xgboost_v1.0.0",
  "triggered_rules": [
    "NEW_COUNTRY_AND_HIGH_AMOUNT",
    "VELOCITY_BURST_1H",
    "UNRECOGNIZED_DEVICE"
  ],
  "latency_breakdown_ms": {
    "feature_enrichment": 1.4,
    "inference": 12.1,
    "risk_engine": 2.3,
    "total": 15.8
  },
  "evaluated_at": "2026-10-01T12:15:30.016Z"
}
```

---

### 3.3 `GET /api/v1/transactions/{transaction_id}/explanation`
Retrieves SHAP TreeExplainer breakdown for a transaction.
```json
// Response: 200 OK
{
  "transaction_id": "TXN-8839210",
  "base_value": 0.018,
  "prediction_value": 0.865,
  "top_positive_features": [
    { "feature": "amount_to_avg_ratio", "value": 37.5, "shap_value": 0.382 },
    { "feature": "country_is_new", "value": 1.0, "shap_value": 0.245 },
    { "feature": "transactions_last_1h", "value": 8.0, "shap_value": 0.174 }
  ],
  "top_negative_features": [
    { "feature": "is_common_mcc", "value": 1.0, "shap_value": -0.042 },
    { "feature": "customer_age_days", "value": 412.0, "shap_value": -0.018 }
  ]
}
```

---

### 3.4 `GET /api/v1/customers/{customer_id}/profile`
Returns behavioral historical baselines stored in PostgreSQL and Redis.
```json
// Response: 200 OK
{
  "customer_id": "CUST-10492",
  "home_country": "IN",
  "historical_average_amount": 1200.00,
  "historical_std_amount": 450.00,
  "max_recorded_amount": 3800.00,
  "known_devices": ["DEV-MOBILE-01", "DEV-LAPTOP-04"],
  "known_countries": ["IN"],
  "recent_velocity": {
    "count_last_1h": 8,
    "count_last_24h": 12,
    "amount_last_1h": 46200.00
  },
  "risk_tier": "ELEVATED"
}
```

---

### 3.5 `GET /api/v1/dashboard/summary`
Live summary KPIs for dashboard header metrics.
```json
// Response: 200 OK
{
  "time_window": "last_24h",
  "total_transactions": 28450,
  "throughput_tps": 5.4,
  "fraud_rate_pct": 1.42,
  "average_risk_score": 14.8,
  "decisions": {
    "approved": 27420,
    "review": 630,
    "blocked": 400
  },
  "p95_latency_ms": 28.4
}
```
