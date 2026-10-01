# System Architecture Specification

---

## 1. Executive Architectural Overview

The **Real-Time Payment Fraud Detection & Risk Engine** is an event-driven, distributed fraud decision platform designed to evaluate financial transactions under strict latency bounds ($< 60$ ms p95). 

The platform separates:
1. **Asynchronous streaming ingestion and stateful enrichment** (Kafka, Redis),
2. **Stateless machine learning and anomaly inference** (XGBoost, Isolation Forest, SHAP),
3. **Deterministic policy arbitration and cost-sensitive scoring** (Risk Engine), and
4. **Synchronous query interfaces and forensic audit trails** (FastAPI, PostgreSQL, Next.js).

```mermaid
flowchart TD
    subgraph CLIENTS["Transaction Sources"]
        SIM[Transaction Simulator / Load Generator]
        POS[E-Commerce / Merchant Gateway API]
    end

    subgraph INGESTION["Streaming Message Bus (Kafka)"]
        K_RAW["Topic: transactions.raw"]
        K_FEAT["Topic: transactions.features"]
        K_PRED["Topic: transactions.predictions"]
        K_DEC["Topic: transactions.decisions"]
        K_DLQ["Topic: transactions.dlq"]
    end

    subgraph STATE["Online State Store (Redis)"]
        REDIS[("Redis 7 (In-Memory Cluster)<br/>- Velocity Counters (1m, 5m, 1h, 24h)<br/>- Customer Historical Geographies<br/>- Known Device Sets<br/>- Moving Average & StdDev")]
    end

    subgraph SERVICES["Pipeline Microservices"]
        FS["Feature Enrichment Service<br/>(Reads Redis previous state,<br/>calculates features, updates Redis post-eval)"]
        IS["ML Inference Service<br/>(XGBoost + Calibrator + Isolation Forest + SHAP)"]
        RE["Risk Decision Engine<br/>(Arbitrates ML probability, anomaly score,<br/>and deterministic rules into 0-100 score)"]
    end

    subgraph PERSISTENCE["Durable Storage & Audit (PostgreSQL)"]
        DB[("PostgreSQL 16<br/>- Transactions<br/>- Enriched Features<br/>- Risk Scores & Decisions<br/>- SHAP Explainability Vectors<br/>- Feedback & Dispute Labels")]
    end

    subgraph PRESENTATION["API & Investigation Dashboard"]
        API["FastAPI Backend<br/>(Sync Scoring, Metrics, Forensic Queries)"]
        UI["Next.js 14 Dashboard<br/>(Real-Time Stream, Deep-Dive Investigation,<br/>Customer Behavioral Profile, Model Observability)"]
        PROM["Prometheus Engine"]
        GRAF["Grafana Dashboards"]
    end

    SIM -->|Publish Event| K_RAW
    POS -->|POST /transactions/score| API
    API -->|Synchronous or Publish| K_RAW

    K_RAW --> FS
    FS <-->|1. Read Previous State| REDIS
    FS -->|2. Emit Features| K_FEAT
    
    K_FEAT --> IS
    IS -->|3. Emit Inference & SHAP| K_PRED

    K_PRED --> RE
    RE -->|4. Emit Final Decision| K_DEC
    RE -.->|On Critical Failure| K_DLQ

    K_DEC --> DB
    K_DEC -.->|Update Online State post-decision| REDIS

    DB <--> API
    API <--> UI
    API --> PROM
    PROM --> GRAF
```

---

## 2. Component Responsibilities & Service Boundaries

| Service / Component | Runtime | Primary Responsibility | Data Read | Data Write |
| :--- | :--- | :--- | :--- | :--- |
| **Transaction Generator** | Python (asyncio) | Generates synthetic transactions with realistic customer/merchant profiles, injecting controlled fraud scenarios (velocity attacks, impossible travel, high-amount anomalies). | Synthetic profile registry | Kafka (`transactions.raw`) |
| **Feature Enrichment Service** | Python (Kafka Consumer) | Ingests raw events, retrieves historical customer/device state from Redis *before* mutating it, computes $\ge 25$ features, and forwards enriched vectors. | Kafka (`transactions.raw`), Redis | Kafka (`transactions.features`) |
| **ML Inference Service** | Python (XGBoost, SHAP) | Loads active champion model artifacts, runs classification, evaluates probability calibration (Isotonic), scores unsupervised anomaly (Isolation Forest), and computes SHAP vectors. | Kafka (`transactions.features`), Local Model Registry | Kafka (`transactions.predictions`) |
| **Risk Decision Engine** | Python | Evaluates deterministic business rules, normalizes signals, runs multi-factor weighted arbitration, assigns risk score (0–100), and classifies into `APPROVE`, `REVIEW`, or `BLOCK`. | Kafka (`transactions.predictions`) | Kafka (`transactions.decisions`), PostgreSQL, Redis (mutates state) |
| **FastAPI Backend** | Python (Uvicorn, AsyncPG) | Exposes synchronous scoring endpoints (`/transactions/score`), forensic query endpoints for analyst dashboard, and Prometheus metrics. | PostgreSQL, Redis, Model Registry | PostgreSQL, Kafka |
| **Next.js 14 Dashboard** | TypeScript, React, Tailwind | Renders live transaction stream, forensic investigation view with SHAP waterfall plots, customer profiles, and model performance curves. | FastAPI REST Endpoints | FastAPI (Dispute label submissions) |
| **PostgreSQL** | Relational RDBMS | Durable storage of all evaluated transactions, features, model versions, audit logs, and feedback labels. | Read by FastAPI / Analysts | Written by Risk Engine / API |
| **Redis** | In-Memory Key-Value Store | Microsecond sliding-window state storage (velocity counts, device sets, historical spend statistics). | Read by Feature Service | Mutated post-evaluation |

---

## 3. Transaction Sequence Flow

The following sequence diagram outlines the lifecycle of an incoming payment transaction:

```mermaid
sequenceDiagram
    autonumber
    actor Merchant as Merchant / Generator
    participant KafkaRaw as Kafka: transactions.raw
    participant FeatureSvc as Feature Enrichment Service
    participant Redis as Redis State Cache
    participant KafkaFeat as Kafka: transactions.features
    participant InferenceSvc as ML Inference Service
    participant RiskEngine as Risk Engine
    participant KafkaDec as Kafka: transactions.decisions
    participant Postgres as PostgreSQL Storage
    participant API as FastAPI Backend
    actor Analyst as Analyst (Next.js Dashboard)

    Merchant->>KafkaRaw: Publish Transaction Payload (TXN-101)
    KafkaRaw->>FeatureSvc: Consume TXN-101
    FeatureSvc->>Redis: Fetch previous customer state (velocity, avg spend, known devices)
    Redis-->>FeatureSvc: Return historical state (prior to TXN-101)
    Note over FeatureSvc: Compute 25+ features (z-score, velocity, travel distance) without leakage
    FeatureSvc->>KafkaFeat: Publish Enriched Features
    
    KafkaFeat->>InferenceSvc: Consume Enriched Features
    Note over InferenceSvc: 1. Predict raw margin via XGBoost<br/>2. Apply Isotonic Calibration (0-1)<br/>3. Compute Isolation Forest Anomaly Score<br/>4. Calculate SHAP contribution values
    InferenceSvc->>RiskEngine: Pass Calibrated Probability + Anomaly + SHAP

    Note over RiskEngine: 1. Evaluate Deterministic Rules<br/>2. Compute Composite Risk Score (0-100)<br/>3. Apply Threshold Policy (APPROVE / REVIEW / BLOCK)
    RiskEngine->>Postgres: Persist Transaction, Features, Risk Score, and Decision
    RiskEngine->>Redis: Update Customer State (Add TXN-101 to sliding window)
    RiskEngine->>KafkaDec: Publish Decision Event (TXN-101: BLOCK, Score: 88.5)

    Analyst->>API: GET /transactions/TXN-101
    API->>Postgres: Query transaction record, features & SHAP
    Postgres-->>API: Return forensic record
    API-->>Analyst: Render Investigation View & SHAP Waterfall
```

---

## 4. Synchronous vs. Asynchronous Communication Boundaries

1. **Asynchronous Streaming Path (Core Transaction Pipeline)**:
   - Utilizes Apache Kafka for durable, partitioned, at-least-once message delivery.
   - De-couples feature extraction from machine learning inference and rule execution.
   - Ensures backpressure absorption during sudden transaction bursts (e.g., Black Friday peak loads).
2. **Synchronous HTTP Path (API & Dashboard)**:
   - Direct `POST /transactions/score` endpoint provided for clients requiring an immediate synchronous HTTP response.
   - The API evaluates the transaction in-process using cached model instances and Redis, returns the decision synchronously, and asynchronously dispatches the event to Kafka/PostgreSQL for durable audit.
   - All dashboard operations (investigation lookup, customer profile, model performance stats) query PostgreSQL via FastAPI asynchronously.

---

## 5. Failure Paths & Graceful Degradation

| Failure Mode | Impact | Recovery / Mitigation Strategy |
| :--- | :--- | :--- |
| **Redis Inaccessible / Timeout** | Real-time sliding window features (1h velocity, z-scores) unavailable. | **Degraded Feature Mode**: System falls back to payload-only features (amount, time of day, MCC), flags transaction as `DEGRADED_STATE`, increases base rule suspicion, and logs critical alert. |
| **Kafka Broker Failure** | Event buffer unavailable for streaming pipeline. | Transactions submitted via synchronous API fail over to local synchronous evaluation and append-only write to PostgreSQL with immediate alert dispatch. |
| **ML Inference Crash / OOM** | ML models unable to produce calibrated probability. | **Deterministic Fallback**: Risk Engine triggers rule-only evaluation mode. If transaction amount $> 3 \times$ customer ceiling or foreign country, transaction defaults to `REVIEW`. |
| **PostgreSQL Write Latency** | Audit persistence slowed. | Asynchronous batch commits via connection pooling (`AsyncPG`). Transient DB disconnects buffer decisions in Kafka topics until reconnected. |
| **Malformed Payload / Schema Drift** | Unparseable transaction JSON. | Event rejected immediately to `transactions.dlq` (Dead Letter Queue) with explicit error payload and stack trace for operator analysis. |

---

## 6. Scalability & Partitioning Strategy

1. **Kafka Partitioning**:
   - Topics are partitioned by `customer_id`.
   - **Critical Property**: Partitioning by `customer_id` guarantees that all transactions for a given customer arrive at the Feature Service strictly in chronological order, eliminating out-of-order state race conditions.
2. **Redis In-Memory State**:
   - Customer keys are hashed (`customer:{customer_id}:*`). Redis cluster hash slots distribute state evenly across memory nodes.
   - Sliding windows utilize sorted sets (`ZREMRANGEBYSCORE` and `ZADD`) with an automatic TTL of 30 days to bound memory growth.
3. **Stateless Service Scaling**:
   - Feature Enrichment, ML Inference, and Risk Engine consumers can scale horizontally up to the number of Kafka topic partitions.
