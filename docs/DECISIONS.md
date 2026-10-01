# Architecture Decision Records (ADRs)

---

## Index of Decisions

- [ADR-001: Selection of Apache Kafka for Message Streaming](#adr-001-selection-of-apache-kafka-for-message-streaming)
- [ADR-002: Selection of Redis for Online Behavioral State](#adr-002-selection-of-redis-for-online-behavioral-state)
- [ADR-003: Selection of PostgreSQL for Durable Persistence and Audit](#adr-003-selection-of-postgresql-for-durable-persistence-and-audit)
- [ADR-004: Selection of XGBoost as Primary Supervised Classifier](#adr-004-selection-of-xgboost-as-primary-supervised-classifier)
- [ADR-005: Adoption of Chronological Splitting (Temporal Validation)](#adr-005-adoption-of-chronological-splitting-temporal-validation)
- [ADR-006: Mandatory Probability Calibration (Isotonic Regression)](#adr-006-mandatory-probability-calibration-isotonic-regression)
- [ADR-007: Architectural Decoupling of ML Inference and Risk Engine](#adr-007-architectural-decoupling-of-ml-inference-and-risk-engine)
- [ADR-008: Inclusion of Unsupervised Anomaly Detection (Isolation Forest)](#adr-008-inclusion-of-unsupervised-anomaly-detection-isolation-forest)
- [ADR-009: Adoption of TreeSHAP for Real-Time Decision Attribution](#adr-009-adoption-of-treeshap-for-real-time-decision-attribution)
- [ADR-010: Idempotency Key Design and Deduplication Strategy](#adr-010-idempotency-key-design-and-deduplication-strategy)

---

### ADR-001: Selection of Apache Kafka for Message Streaming
- **Context**: Ingesting high-velocity payment streams requires a buffer that decouples producers from consumers, absorbs sudden traffic spikes, and provides ordered delivery per customer.
- **Decision**: Adopt Apache Kafka as the distributed event streaming backbone.
- **Reason**: Kafka provides immutable commit logs, partition-level ordered delivery when keyed by `customer_id`, and independent consumer groups.
- **Alternatives Considered**: RabbitMQ (lacks durable replayable commit log at scale), AWS SQS (cloud-vendor lock-in, higher latency), In-Memory Python Queues (no crash recovery or multi-process distribution).
- **Tradeoffs**: Higher operational complexity (Zookeeper/Kraft coordination, JVM memory overhead).
- **Consequences**: Architecture guarantees at-least-once delivery; consumers must be idempotent.

---

### ADR-002: Selection of Redis for Online Behavioral State
- **Context**: Real-time feature enrichment requires computing sliding-window counters (1m, 1h velocity, moving averages) in $< 2$ milliseconds during transaction flight.
- **Decision**: Use Redis in-memory datastore for online customer behavioral state.
- **Reason**: Sub-millisecond read/write latency; native support for Sorted Sets (`ZSET`) enabling exact time-bounded sliding windows via `ZREMRANGEBYSCORE` and `ZCOUNT`.
- **Alternatives Considered**: Direct PostgreSQL queries (too slow under high concurrency), In-memory Python dictionaries (cannot share state across scaled consumer instances).
- **Tradeoffs**: Volatile memory requires RDB/AOF persistence; requires strict TTL management to avoid unbounded memory growth.
- **Consequences**: Fast enrichment path; system must support graceful degradation if Redis is temporarily unreachable.

---

### ADR-003: Selection of PostgreSQL for Durable Persistence and Audit
- **Context**: Financial decisions require ACID compliance, relational integrity, complex analyst filtering, and long-term compliance auditability.
- **Decision**: Use PostgreSQL 16 as the system of record.
- **Reason**: Strong relational constraints, foreign keys ensuring data integrity, JSONB support for dynamic feature and SHAP vectors, and robust indexing.
- **Alternatives Considered**: MongoDB (weaker schema guarantees for financial audits), Cassandra (optimized for write throughput, but complex queries and joins for investigation dashboard are prohibitive).
- **Tradeoffs**: Write throughput is bounded by disk I/O; requires connection pooling (`AsyncPG`).
- **Consequences**: Provides reliable ground truth for the investigation dashboard and retraining feedback loops.

---

### ADR-004: Selection of XGBoost as Primary Supervised Classifier
- **Context**: Tabular fraud detection requires models capable of modeling complex feature interactions (e.g., amount $\times$ country $\times$ velocity) with ultra-low scoring latency.
- **Decision**: Deploy XGBoost as the primary champion supervised model.
- **Reason**: Consistently achieves superior PR-AUC on tabular benchmarks; native handling of missing values; supports gradient-weighted class imbalance (`scale_pos_weight`); scoring latency $< 10$ ms.
- **Alternatives Considered**: Deep Neural Networks / TabNet (higher training overhead, higher inference latency, difficult hyperparameter tuning on small-to-medium datasets), Random Forest (larger model size, slower inference).
- **Tradeoffs**: Susceptible to uncalibrated probability outputs; requires hyperparameter tuning to avoid overfitting.
- **Consequences**: Outputs must pass through a calibration layer before being consumed by the Risk Engine.

---

### ADR-005: Adoption of Chronological Splitting (Temporal Validation)
- **Context**: Payment fraud evolves temporally. Random cross-validation leaks future card testing behavior and customer spending profiles into the past.
- **Decision**: Enforce strict chronological splitting across all validation and benchmarking pipelines.
- **Reason**: Accurately simulates the production reality where models are trained on historical data and deployed to score unseen future transactions.
- **Alternatives Considered**: Stratified K-Fold CV (causes lookahead bias and over-optimistic PR-AUC).
- **Tradeoffs**: Slightly smaller effective training windows compared to full-dataset shuffling.
- **Consequences**: All reported metrics reflect realistic production generalization.

---

### ADR-006: Mandatory Probability Calibration (Isotonic Regression)
- **Context**: The downstream Risk Engine treats model outputs as actual financial risk likelihoods. Raw tree outputs are distorted toward decision boundaries.
- **Decision**: Pass raw XGBoost outputs through an Isotonic Regression calibrator fitted on held-out validation data.
- **Reason**: Calibrated probabilities align directly with empirical fraud rates (e.g., predicted $0.80$ corresponds to $80$ fraud cases per $100$ transactions), minimizing the Brier score.
- **Alternatives Considered**: Platt Scaling (parametric sigmoid; can underfit if distortion is non-sigmoidal), Raw Probability (violates risk cost model assumptions).
- **Tradeoffs**: Requires a non-overlapping validation split to prevent overfitting the step function.
- **Consequences**: Risk Engine can reliably combine ML probabilities with financial cost models.

---

### ADR-007: Architectural Decoupling of ML Inference and Risk Engine
- **Context**: A model predicting $0.85$ fraud probability should not unilaterally block transactions without evaluating customer tier, regulatory compliance, and business rules.
- **Decision**: Decouple ML Inference into a statistical provider, and establish a separate Risk Engine for decision arbitration.
- **Reason**: Risk policies, thresholds, and business rules change much faster than model training cycles; allows fraud analysts to adjust thresholds without redeploying ML models.
- **Alternatives Considered**: End-to-end classification directly outputting `APPROVE`/`BLOCK` (inflexible, opaque, couples business logic with model weights).
- **Tradeoffs**: Introduces an extra computation hop ($\approx 2$ ms).
- **Consequences**: Clean separation of concerns and clear auditability.

---

### ADR-008: Inclusion of Unsupervised Anomaly Detection (Isolation Forest)
- **Context**: Supervised models only detect fraud patterns present in historical training labels. Zero-day attacks and novel exploit vectors evade supervised classifiers.
- **Decision**: Integrate Isolation Forest to generate an independent unsupervised anomaly score.
- **Reason**: Flags structural outliers in spending velocity and multidimensional feature space without requiring prior labels.
- **Alternatives Considered**: Local Outlier Factor (LOF) (computationally prohibitive at runtime; $O(N)$ nearest neighbor lookups), Autoencoders (heavyweight inference).
- **Tradeoffs**: Anomaly $\neq$ Fraud; introduces false positives if used in isolation.
- **Consequences**: Anomaly score is treated as an auxiliary input to the Risk Engine rather than an autonomous decision maker.

---

### ADR-009: Adoption of TreeSHAP for Real-Time Decision Attribution
- **Context**: Fraud analysts reviewing flagged transactions need immediate, mathematically grounded reasons for why a transaction was flagged.
- **Decision**: Compute TreeSHAP values for all evaluated transactions.
- **Reason**: SHAP provides game-theoretic additive local attributions that sum exactly to the model output margin.
- **Alternatives Considered**: LIME (sampling-based, non-deterministic, slow for real-time), Permutation Importance (global only, not per-transaction).
- **Tradeoffs**: Real-time SHAP calculation adds $5 - 15$ ms to inference time.
- **Consequences**: Analyst investigation dashboard displays clear, verified feature contribution waterfalls.

---

### ADR-010: Idempotency Key Design and Deduplication Strategy
- **Context**: Network hiccups, client retries, or Kafka rebalances can result in the same payment transaction being ingested multiple times.
- **Decision**: Enforce idempotency via a SHA-256 hash stored in Redis with a 24-hour TTL and backed by a database unique constraint.
- **Reason**: Prevents duplicate fraud alerts, double-charging, or corrupting customer rolling behavioral metrics.
- **Alternatives Considered**: Relying solely on database unique key exceptions (causes unnecessary database load and connection pool contention).
- **Tradeoffs**: Additional Redis lookup per transaction ($< 0.5$ ms).
- **Consequences**: The system is completely safe against duplicate message replays.
