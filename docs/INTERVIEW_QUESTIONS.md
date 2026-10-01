# Technical Interview Handbook: 50+ Deep-Dive Questions & Answers

This document serves as the master interview reference for the **Real-Time Payment Fraud Detection & Risk Engine**.
Every question follows a structured format:
- **QUESTION**
- **SHORT ANSWER**
- **DEEP EXPLANATION**
- **WHERE IT APPEARS IN THIS PROJECT**

---

## Category 1: Machine Learning & Statistical Foundations

### Q1. Why is Accuracy a dangerous and misleading metric in Fraud Detection?
- **SHORT ANSWER**: In highly imbalanced datasets, predicting the majority class yields high accuracy while completely failing to identify fraud.
- **DEEP EXPLANATION**: If $99\%$ of payment transactions are legitimate ($1\%$ fraud), a trivial model predicting "Legitimate" for every transaction achieves $99\%$ accuracy, $0\%$ recall, and infinite business loss. Fraud detection requires imbalance-aware metrics: Precision-Recall Area Under Curve (PR-AUC), Recall at fixed False-Positive Rate, and Brier Score.
- **WHERE IT APPEARS IN THIS PROJECT**: Documented in `docs/ML_PIPELINE.md` Section 7; implemented in `ml/src/evaluation/metrics.py`.

### Q2. What is the mathematical difference between ROC-AUC and PR-AUC, and why prefer PR-AUC for fraud?
- **SHORT ANSWER**: ROC-AUC evaluates True Positive Rate against False Positive Rate ($FP / (FP + TN)$); because True Negatives ($TN$) are massive in fraud, $FPR$ stays artificially low. PR-AUC evaluates Precision ($TP / (TP + FP)$) directly against Recall ($TP / (TP + FN)$), making false positives immediately visible.
- **DEEP EXPLANATION**: When legitimate cases outnumber fraud by 100:1, adding 1,000 false positives hardly shifts the ROC curve because the denominator $(FP + TN)$ is dominated by millions of legitimate transactions. In contrast, Precision drops sharply from $0.90$ to $0.10$, accurately reflecting severe analyst alert fatigue.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/ML_PIPELINE.md` Section 7; primary model selection criterion in `ml/train.py`.

### Q3. What is Temporal Data Leakage in time-series tabular data?
- **SHORT ANSWER**: Using future information—either directly or via aggregate statistics—to make predictions about the past.
- **DEEP EXPLANATION**: In fraud detection, calculating a customer's rolling 30-day average spend using all transactions in a dataset includes future purchases that haven't occurred yet at the time of scoring. This creates unrealistic model performance during offline testing that collapses in production.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/FEATURE_ENGINEERING.md` Section 1; automated regression test in `tests/ml/test_temporal_leakage.py`.

### Q4. Why is random K-Fold cross-validation invalid for payment fraud models?
- **SHORT ANSWER**: Random shuffling breaks chronological causality and leaks fraudster behavior patterns across train and test folds.
- **DEEP EXPLANATION**: Fraud attacks frequently occur in rapid clusters (velocity card testing). Random splitting assigns event 1 to train and event 2 to test. The model learns to identify the specific card or attacker identity rather than generalizable fraud indicators.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/ML_PIPELINE.md` Section 2; temporal split script in `ml/src/data/splitter.py`.

### Q5. What is the Brier Score, and why does it matter?
- **SHORT ANSWER**: The mean squared error between predicted probabilities and actual binary outcomes ($y \in \{0, 1\}$).
- **DEEP EXPLANATION**: Defined as $\text{BS} = \frac{1}{N} \sum_{i=1}^N (\hat{p}_i - y_i)^2$. Unlike log loss, which heavily penalizes confident mistakes asymptotically, Brier score can be decomposed into Uncertainty, Reliability (calibration), and Resolution (discrimination), directly measuring whether probabilities represent true frequencies.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/ML_PIPELINE.md` Section 5; calibration scoring in `ml/src/calibration/calibrator.py`.

---

## Category 2: Supervised Algorithms (Logistic Regression, Random Forest, XGBoost)

### Q6. How does Logistic Regression serve as a baseline in this architecture?
- **SHORT ANSWER**: It provides a convex, highly interpretable linear reference point that operates in sub-millisecond latency.
- **DEEP EXPLANATION**: Logistic regression computes $\sigma(\mathbf{w}^T \mathbf{x} + b)$. Its weights indicate exact log-odds shifts per feature. However, it cannot natively capture non-linear conjunctions (e.g., high amount *only* when accompanied by an unfamiliar country) without manual polynomial feature crosses.
- **WHERE IT APPEARS IN THIS PROJECT**: `ml/src/models/logistic_baseline.py` and benchmarked in `docs/EXPERIMENTS.md` (EXP-001).

### Q7. How does Random Forest mitigate overfitting compared to individual Decision Trees?
- **SHORT ANSWER**: By ensembling decorrelated trees via bootstrap aggregating (bagging) and random feature subspace projection.
- **DEEP EXPLANATION**: Individual deep decision trees have low bias but high variance. Random Forest trains $B$ trees on bootstrap samples and restricts split evaluations to a random subset of features ($\sqrt{p}$). Averaging predictions reduces variance by a factor proportional to $\frac{1}{B} + \frac{B-1}{B}\rho$, where $\rho$ is tree correlation.
- **WHERE IT APPEARS IN THIS PROJECT**: `ml/src/models/random_forest_baseline.py` (EXP-002).

### Q8. How does Gradient Boosting in XGBoost differ from Bagging in Random Forest?
- **SHORT ANSWER**: Bagging trains trees in parallel independently; Gradient Boosting trains trees sequentially, with each new tree fitting the negative gradient (pseudo-residuals) of the loss function.
- **DEEP EXPLANATION**: XGBoost optimizes an objective function with second-order Taylor expansion: $\mathcal{L}^{(t)} \approx \sum [g_i f_t(x_i) + \frac{1}{2} h_i f_t^2(x_i)] + \Omega(f_t)$, where $g_i$ and $h_i$ are first and second derivatives of the loss. It penalizes tree complexity ($\gamma T + \frac{1}{2}\lambda \sum w^2$), resulting in superior tabular accuracy.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/ML_PIPELINE.md` Section 3; champion training script `ml/src/models/xgboost_model.py`.

### Q9. What does `scale_pos_weight` do in XGBoost, and what is the trade-off?
- **SHORT ANSWER**: It scales the gradients of positive class instances by $N_{\text{neg}} / N_{\text{pos}}$, heavily penalizing false negatives.
- **DEEP EXPLANATION**: By inflating positive loss gradients, tree splits prioritize isolating fraud instances, increasing Recall. The trade-off is that raw predicted probabilities become uncalibrated and systematically skewed toward $1.0$, requiring subsequent probability calibration.
- **WHERE IT APPEARS IN THIS PROJECT**: `ml/src/models/xgboost_model.py` and `docs/EXPERIMENTS.md` (EXP-005).

### Q10. Why is SMOTE (Synthetic Minority Over-sampling) risky for temporal transaction data?
- **SHORT ANSWER**: It creates synthetic data points by linear interpolation in feature space, violating physical velocity and chronological sequence constraints.
- **DEEP EXPLANATION**: If a cardholder has a $100 transaction in Mumbai at 10:00 AM and a $1,200 transaction in Delhi at 8:00 PM, SMOTE might synthesize an intermediate point with $650 at 2:00 PM with artificial coordinates that make no real-world behavioral sense, causing model distortion.
- **WHERE IT APPEARS IN THIS PROJECT**: Discussed in `docs/ML_PIPELINE.md` Section 4; ADR-005 in `docs/DECISIONS.md`.

---

## Category 3: Probability Calibration & Explainability (SHAP)

### Q11. Why are raw probabilities from tree-based ensembles (XGBoost/Random Forest) uncalibrated?
- **SHORT ANSWER**: Tree leaf averaging and boosting regularization push predictions toward extremes (0 and 1) or cluster near split thresholds rather than matching true empirical frequencies.
- **DEEP EXPLANATION**: A tree leaf containing 5 samples might yield a fraction of $1.0$, but that does not mean there is a $100\%$ true probability of fraud. In XGBoost, the sigmoid transformation applied to log-odds margins produces rank-ordered scores, not calibrated likelihoods.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/ML_PIPELINE.md` Section 5; ADR-006 in `docs/DECISIONS.md`.

### Q12. What is the difference between Platt Scaling and Isotonic Regression?
- **SHORT ANSWER**: Platt Scaling is parametric (fits a logistic sigmoid curve); Isotonic Regression is non-parametric (fits a monotonically increasing piecewise step function).
- **DEEP EXPLANATION**: Platt Scaling assumes the calibration mapping follows a sigmoid $\frac{1}{1 + \exp(Af + B)}$. Isotonic Regression makes no functional form assumption, making it more flexible when large validation sets are available, though prone to overfitting on small sets.
- **WHERE IT APPEARS IN THIS PROJECT**: `ml/src/calibration/calibrator.py`; benchmarked in `docs/EXPERIMENTS.md` (EXP-006).

### Q13. How does TreeSHAP work mathematically?
- **SHORT ANSWER**: It computes Shapley values from cooperative game theory in polynomial time by traversing tree decision paths.
- **DEEP EXPLANATION**: For an ensemble model $f(x)$, TreeSHAP attributes the deviation from the expected base value $E[f(X)]$ across features: $f(x) - E[f(x)] = \sum_{j=1}^M \phi_j$. It evaluates conditional expectations $E[f(x)|x_S]$ by recursively tracking sample counts along tree branches.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/ML_PIPELINE.md` Section 8; `ml/src/explainability/shap_explainer.py`.

### Q14. What is the operational difference between Global Feature Importance and Local SHAP values?
- **SHORT ANSWER**: Global importance (e.g., gain/permutation) tells you what features matter across the entire dataset; local SHAP values explain why a *single specific transaction* was flagged.
- **DEEP EXPLANATION**: In an investigation dashboard, an analyst does not care that "amount" is globally important. They need to know that for *Transaction #991*, the score was elevated specifically because `country_is_new = 1` ($+0.25$) and `amount_zscore = 4.2` ($+0.38$).
- **WHERE IT APPEARS IN THIS PROJECT**: Visualized in Next.js investigation view; returned via `/api/v1/transactions/{id}/explanation`.

---

## Category 4: Behavioral Analytics & Anomaly Detection

### Q15. How do you compute a customer's rolling spending Z-score in real-time?
- **SHORT ANSWER**: Store customer running mean $\mu_{t-1}$ and variance $\sigma^2_{t-1}$ in Redis or DB; compute $Z = (x_t - \mu_{t-1}) / (\sigma_{t-1} + \epsilon)$.
- **DEEP EXPLANATION**: Welford's algorithm or exponential moving averages allow $O(1)$ incremental updates to mean and variance without scanning millions of historical rows. Crucially, the current transaction $x_t$ must not be included in $\mu$ or $\sigma$ during the $Z$ calculation.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/FEATURE_ENGINEERING.md` Section 3; `services/feature_service/enricher.py`.

### Q16. Why is Anomaly Detection separate from Fraud Classification?
- **SHORT ANSWER**: An anomaly is a statistical outlier; fraud is intentional malicious deception. An anomaly is an informative risk signal, not definitive proof of crime.
- **DEEP EXPLANATION**: An executive buying an expensive international airline ticket is an extreme statistical anomaly (high amount, new country), but completely legitimate. Conversely, a fraudster performing a ₹200 card test at a local merchant is normal behavior statistically, but fraudulent.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/ML_PIPELINE.md` Section 6; ADR-008 in `docs/DECISIONS.md`.

### Q17. How does the Isolation Forest algorithm isolate anomalies?
- **SHORT ANSWER**: By randomly partitioning feature space; outliers require fewer random binary splits to isolate than normal clustered points.
- **DEEP EXPLANATION**: Normal data points reside in dense regions and require many hyperplanes (deep tree paths) to isolate into a single leaf. Outliers reside in sparse peripheral space and are isolated near the tree root (short path length $h(x)$). Path length is mapped to anomaly score $s \in [0, 1]$.
- **WHERE IT APPEARS IN THIS PROJECT**: `ml/src/anomaly/isolation_forest.py`.

### Q18. How do you detect "Impossible Travel" in payment streaming?
- **SHORT ANSWER**: Calculate the Haversine spatial distance between the current and previous transaction locations, divide by time elapsed, and flag speeds exceeding commercial airline limits ($> 900$ km/h).
- **DEEP EXPLANATION**: If a card is swiped in London at 12:00 PM and in Singapore at 12:30 PM, the distance is $\approx 10,800$ km in $0.5$ hours ($21,600$ km/h). This physical impossibility indicates credential theft, proxy routing, or cloned cards.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/FEATURE_ENGINEERING.md` Section 3; Rule `R01_IMPOSSIBLE_TRAVEL` in `services/risk_engine/rules.py`.

---

## Category 5: Risk Engine & Decision Policies

### Q19. Why should a payment system decouple ML inference from the Risk Engine?
- **SHORT ANSWER**: ML models output statistical estimates; business rules, compliance laws, risk appetites, and cost matrices change independently of model retraining cycles.
- **DEEP EXPLANATION**: If regulatory policies change to require step-up MFA on all transactions over ₹50,000, you should update a risk policy config file in seconds, not retrain and redeploy an XGBoost model.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/RISK_ENGINE.md` Section 1; ADR-007 in `docs/DECISIONS.md`.

### Q20. How is the 0–100 Risk Score calculated in this engine?
- **SHORT ANSWER**: A weighted sum of calibrated ML probability, normalized anomaly score, behavioral variance score, and rule penalties, scaled to $0 - 100$.
- **DEEP EXPLANATION**: 
  $$R = 100 \times \min\left(1.0, w_{\text{ML}} P_{\text{ML}} + w_{\text{anom}} S_{\text{anom}} + w_{\text{behav}} S_{\text{behav}} + w_{\text{rules}} S_{\text{rules}}\right)$$
  Where default weights are $0.55, 0.15, 0.15, 0.15$.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/RISK_ENGINE.md` Section 3; `services/risk_engine/engine.py`.

### Q21. How do you mathematically evaluate False Positive vs. False Negative trade-offs?
- **SHORT ANSWER**: By computing the Expected Financial Cost matrix across different operational thresholds.
- **DEEP EXPLANATION**: 
  $$\mathbb{E}[\text{Cost}] = \text{FN} \times (\text{Amount} + C_{\text{chargeback}}) + \text{FP} \times C_{\text{insult}} + \text{Review} \times C_{\text{analyst}}$$
  Minimizing expected cost determines optimal decision boundaries rather than using arbitrary $0.5$ cutoffs.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/RISK_ENGINE.md` Section 5; `services/risk_engine/cost_model.py`.

---

## Category 6: Real-Time Streaming & Apache Kafka

### Q22. Why use Apache Kafka instead of RabbitMQ or standard HTTP REST queues for this pipeline?
- **SHORT ANSWER**: Kafka provides an immutable, persistent, partitioned commit log with independent consumer group offsets and high-throughput backpressure absorption.
- **DEEP EXPLANATION**: In high-load payment events, downstream ML inference can suffer temporary latency spikes. Kafka acts as a durable shock absorber, retaining unconsumed messages on disk without dropping packets. RabbitMQ stores messages in RAM and degrades under large message backlogs.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/STREAMING.md` Section 1; ADR-001 in `docs/DECISIONS.md`.

### Q23. Why is partitioning Kafka topics by `customer_id` critical?
- **SHORT ANSWER**: Kafka guarantees strict ordering *only within a single partition*; keying by `customer_id` ensures a customer's transactions are processed sequentially.
- **DEEP EXPLANATION**: If Customer A initiates two transactions 100ms apart and they land on different partitions consumed by different workers, Worker 2 might evaluate before Worker 1, causing incorrect velocity calculations and race conditions. Partitioning by customer hash ensures strict serialization per customer.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/STREAMING.md` Section 3; `services/transaction_generator/producer.py`.

### Q24. What is a Kafka Consumer Group Rebalance, and how do you prevent rebalance storms?
- **SHORT ANSWER**: Occurs when consumer membership changes or a consumer exceeds `max.poll.interval.ms`, causing Kafka to revoke and reassign partitions. Prevent by keeping inference processing time well below the poll timeout.
- **DEEP EXPLANATION**: If heavy ML inference or SHAP computation blocks a consumer thread longer than `max.poll.interval.ms`, the broker considers the consumer dead and triggers a rebalance. All consumers stop processing during rebalances. We decouple message fetching from inference worker threadpools to guarantee timely heartbeats.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/STREAMING.md` Section 4; consumer configuration in `services/inference_service/consumer.py`.

### Q25. What is a Dead Letter Queue (DLQ), and when is a message sent there?
- **SHORT ANSWER**: A secondary Kafka topic for messages that fail processing due to non-transient errors (e.g., malformed JSON, schema corruption).
- **DEEP EXPLANATION**: If an unparseable byte string arrives on `transactions.raw`, repeatedly retrying will block the consumer partition indefinitely (a "poison pill"). The consumer catches deserialization exceptions, wraps the error payload, dispatches it to `transactions.dlq`, and commits the offset to unblock the pipeline.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/STREAMING.md` Section 6; `services/feature_service/consumer.py`.

---

## Category 7: In-Memory State & Redis

### Q26. Why is Redis used instead of querying PostgreSQL for rolling features?
- **SHORT ANSWER**: PostgreSQL disk reads take $5 - 20$ ms; Redis serves in-memory queries in $< 1$ ms, preserving our sub-60ms p95 SLA.
- **DEEP EXPLANATION**: Calculating 1-hour transaction counts in PostgreSQL requires indexed `COUNT(*)` range scans. Under hundreds of concurrent transactions per second, this exhausts connection pools and I/O IOPS. Redis sorted sets (`ZCOUNT`) provide $O(\log N + M)$ sub-millisecond aggregations in RAM.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/DATABASE.md` Section 1; ADR-002 in `docs/DECISIONS.md`.

### Q27. How do you implement a sliding-time window in Redis using Sorted Sets (`ZSET`)?
- **SHORT ANSWER**: Store transactions with the UNIX epoch timestamp as the score; purge expired entries using `ZREMRANGEBYSCORE`, and count remaining entries using `ZCOUNT`.
- **DEEP EXPLANATION**: 
  ```text
  1. ZREMRANGEBYSCORE cust:101:window -inf (now - 3600)  # Evict > 1 hour old
  2. ZCOUNT cust:101:window -inf +inf                    # Count txns in window
  3. ZADD cust:101:window (now) (txn_id:amount)          # Add current txn post-eval
  ```
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/INFRASTRUCTURE.md` Section 5; `services/feature_service/redis_state.py`.

### Q28. What happens to the system if Redis crashes or becomes unreachable?
- **SHORT ANSWER**: The system degrades gracefully to `DEGRADED_STATE` mode using payload-only features and deterministic rule safeguards.
- **DEEP EXPLANATION**: When Redis connectivity fails, the Feature Service catches the timeout, returns zero or neutral baseline values for sliding features, attaches a `state_degraded: true` flag, and the Risk Engine raises base suspicion on high-amount transactions until Redis recovers.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/ARCHITECTURE.md` Section 5; `services/feature_service/enricher.py`.

---

## Category 8: Relational Persistence & PostgreSQL

### Q29. Why use PostgreSQL alongside Redis?
- **SHORT ANSWER**: Redis provides fast volatile state; PostgreSQL provides ACID-compliant durable storage, complex SQL relational joins, and audit history.
- **DEEP EXPLANATION**: Redis cannot handle multi-table relational queries required by fraud analysts (e.g., finding all transactions by device X where risk score $> 70$ and dispute outcome was positive). PostgreSQL stores normalized records with JSONB feature snapshots for complete historical reproducibility.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/DATABASE.md` Section 1; ADR-003 in `docs/DECISIONS.md`.

### Q30. How is Idempotency enforced in the database?
- **SHORT ANSWER**: Via unique constraints on `transaction_id` and `idempotency_key` with `ON CONFLICT DO NOTHING` logic.
- **DEEP EXPLANATION**: If a network retry re-delivers an already processed payment event, the database rejects duplicate row creation. The API returns the previously persisted prediction record without double-counting financial state.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/DATABASE.md` Section 2.2; `database/schema.sql`.

---

## Category 9: Backend Engineering & FastAPI

### Q31. Why choose FastAPI over Flask or Django for this engine?
- **SHORT ANSWER**: Native asynchronous I/O (`asyncio`), high-performance ASGI architecture, automatic Pydantic schema validation, and OpenAPI documentation generation.
- **DEEP EXPLANATION**: FastAPI leverages `uvicorn` and `starlette`, achieving throughput comparable to Go/Node.js. Non-blocking asynchronous database (`asyncpg`) and Redis (`aioredis`) calls allow a single worker process to serve thousands of concurrent connections without blocking threads.
- **WHERE IT APPEARS IN THIS PROJECT**: `services/api/main.py`; `docs/API.md`.

### Q32. How does Pydantic ensure runtime safety in the API?
- **SHORT ANSWER**: It parses and validates all incoming JSON payloads against strictly typed Python dataclasses, returning structured HTTP 422 errors for malformed inputs.
- **DEEP EXPLANATION**: Pydantic validates types, ranges (e.g., `amount > 0`), string patterns, and date formats before execution logic is invoked, shielding the ML models from `TypeError` or unexpected `None` values.
- **WHERE IT APPEARS IN THIS PROJECT**: `services/api/schemas.py`.

---

## Category 10: Observability, Drift & MLOps

### Q33. What is the difference between Data Drift and Concept Drift?
- **SHORT ANSWER**: Data Drift is a change in input feature distributions $P(X)$; Concept Drift is a change in the relationship between features and the target $P(Y|X)$.
- **DEEP EXPLANATION**: If a sudden influx of international shoppers appears, the distribution of foreign transactions rises (Data Drift). If fraudsters discover a technique to mimic normal domestic shopping behavior while stealing funds, the fraud distribution changes for the same features (Concept Drift).
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/OBSERVABILITY.md` Section 4.

### Q34. How is Population Stability Index (PSI) calculated?
- **SHORT ANSWER**: 
  $$\text{PSI} = \sum_{b=1}^B (A_b - E_b) \times \ln\left(\frac{A_b}{E_b}\right)$$
  Where $A_b$ is actual observed frequency and $E_b$ is expected baseline frequency in bin $b$.
- **DEEP EXPLANATION**: Bins are constructed from the training feature distribution (typically 10 quantiles). PSI measures distribution divergence. $\text{PSI} < 0.1$ indicates stability, $0.1 - 0.25$ indicates moderate drift, and $> 0.25$ triggers model retraining alerts.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/OBSERVABILITY.md` Section 4.1; `ml/src/evaluation/drift.py`.

### Q35. What key Prometheus metrics should an ML Engineer monitor in real time?
- **SHORT ANSWER**: Prediction latency histograms, binned prediction score distributions, throughput (TPS), Kafka consumer lag, and HTTP error rates.
- **DEEP EXPLANATION**: A sudden collapse in prediction latency usually means the model is returning default fallback values (silent crash). A sudden upward shift in the prediction score histogram indicates covariate shift or an active automated attack.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/OBSERVABILITY.md` Section 2; `services/api/metrics.py`.

---

## Category 11: System Design & Production Resilience

### Q36. How does the system achieve a sub-60ms p95 latency target?
- **SHORT ANSWER**: By utilizing in-memory Redis sliding windows ($< 2$ ms), in-process compiled C++ XGBoost inference ($< 10$ ms), and asynchronous non-blocking event publishing.
- **DEEP EXPLANATION**: High latency in ML pipelines is caused by disk I/O, network roundtrips, and bloated tree sizes. By maintaining all required behavioral features in Redis, caching model artifacts in RAM, and performing async writes to PostgreSQL, the critical evaluation path is purely in-memory.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/PRD.md` Section 4.1; `docs/ARCHITECTURE.md` Section 1.

### Q37. How would this system scale to handle 50,000 transactions per second (Visa scale)?
- **SHORT ANSWER**: Shard Kafka topics across hundreds of partitions, deploy Redis clusters with read replicas, serve models via NVIDIA Triton / ONNX with dynamic batching, and horizontally scale stateless consumer pods on Kubernetes.
- **DEEP EXPLANATION**: Documented as future production blueprint in `docs/DEPLOYMENT.md` Section 4. At 50k TPS, single Python processes are insufficient; inference is delegated to specialized GPU/Inferentia model servers running ONNX Runtime, Redis is replaced with an in-memory memory grid (e.g., Aerospike), and write persistence uses distributed commit logs (Cassandra or ScyllaDB).
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/DEPLOYMENT.md` Section 4.

### Q38. How does the Feedback Loop enable continuous model retraining?
- **SHORT ANSWER**: Fraud analysts review flagged transactions and submit confirmed dispute labels via Next.js; confirmed labels flow into `transactions.feedback` and PostgreSQL for future training datasets.
- **DEEP EXPLANATION**: Fraud has a delayed feedback loop (chargebacks take 30–90 days to settle). The feedback service matches delayed chargeback records against the original feature vector snapshot stored in PostgreSQL, creating ground-truth temporal training datasets without re-computing past features.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/DATABASE.md` (`feedback` & `fraud_labels` tables); `services/api/routers/feedback.py`.

### Q39. What is Champion-Challenger (Shadow) Model Deployment?
- **SHORT ANSWER**: Running a new model ("Challenger") in parallel with the production model ("Champion") on live production traffic without letting Challenger decisions affect customers.
- **DEEP EXPLANATION**: The Challenger scores transactions asynchronously in the background. Metrics, calibration curves, and latency are monitored for weeks. Only when the Challenger statistically outperforms the Champion in PR-AUC and reliability is it promoted to Champion.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/DATABASE.md` (`model_versions` table); `docs/DECISIONS.md`.

### Q40. Why must secrets and credentials never be committed to Git?
- **SHORT ANSWER**: Public or internal code leaks expose infrastructure credentials, allowing attackers to access databases, tamper with models, or exfiltrate data.
- **DEEP EXPLANATION**: All connection strings, passwords, and API keys are injected via runtime environment variables (`.env`) with Git exclusions configured via `.gitignore`.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/SECURITY.md` Section 4; `.env.example`.

---

## Category 12: Fraud Typologies & Domain Edge Cases

### Q41. What is Card-Not-Present (CNP) Fraud, and how does this engine detect it?
- **SHORT ANSWER**: Fraud where neither the physical card nor cardholder is present (online e-commerce). Detected via device fingerprint changes, unfamiliar IP geolocations, and rapid spending velocity.
- **DEEP EXPLANATION**: Stolen card numbers purchased on darknet forums are used online. The physical card is genuine, but the user is fraudulent. Features like `is_new_device`, `is_new_country`, and `impossible_travel` target CNP patterns.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/FEATURE_ENGINEERING.md`; simulated in `services/transaction_generator/scenarios.py`.

### Q42. What is a "Velocity Attack" / Card Testing?
- **SHORT ANSWER**: Automated bots attempting micro-transactions across hundreds of cards or rapid succession on one card to verify validity before large purchases.
- **DEEP EXPLANATION**: Characterized by sudden bursts of transactions within seconds or minutes. Detected via sliding-window Redis counters `txn_count_1m >= 3` and rule `R02_VELOCITY_BURST_1M`.
- **WHERE IT APPEARS IN THIS PROJECT**: `services/risk_engine/rules.py`; `docs/RISK_ENGINE.md`.

### Q43. What is Account Takeover (ATO)?
- **SHORT ANSWER**: A fraudster gaining unauthorized access to an existing legitimate user's account via credential stuffing or session hijacking.
- **DEEP EXPLANATION**: The historical account baseline has months of normal behavior, followed by an immediate shift: new device login, sudden password change, and large monetary transfers. Detected via `is_new_device` paired with extreme `customer_amount_zscore`.
- **WHERE IT APPEARS IN THIS PROJECT**: Rule `R03_NEW_DEVICE_HIGH_AMOUNT` in `services/risk_engine/rules.py`.

### Q44. What is Device Sharing Anomaly in fraud syndicates?
- **SHORT ANSWER**: When a single physical device is observed making payments across dozens of completely distinct customer accounts within a short window.
- **DEEP EXPLANATION**: Fraud rings operate specialized workstations or emulators. Legitimate devices are used by 1–2 family members. A device logging into 5+ unique customer IDs in 24 hours triggers `R05_DEVICE_SHARING_ANOMALY`.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/FEATURE_ENGINEERING.md` (`device_customer_count`).

### Q45. How does the engine prevent "Friendly Fraud" (Chargeback Fraud)?
- **SHORT ANSWER**: By maintaining an immutable audit log of device fingerprints, IP addresses, timestamps, and customer historical baselines to defend against false dispute claims.
- **DEEP EXPLANATION**: Friendly fraud occurs when a genuine customer makes a purchase and later falsely claims it was unauthorized to get a refund. Storing device hashes, geolocations, and previous transaction histories in PostgreSQL provides merchant dispute evidence.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/DATABASE.md` (`audit_events` & `transactions` tables).

---

## Category 13: Architecture & Coding Agent Directives

### Q46. What is the Canonical Source of Truth in this repository?
- **SHORT ANSWER**: The documentation hierarchy: `PRD.md` $\to$ `docs/ARCHITECTURE.md` $\to$ `docs/INFRASTRUCTURE.md` $\to$ Schema/API docs $\to$ Code.
- **DEEP EXPLANATION**: Architecture and contracts are documented before code is written. If code changes alter an interface or model, the documentation and `docs/DECISIONS.md` must be updated first.
- **WHERE IT APPEARS IN THIS PROJECT**: `AGENTS.md` Section 2; `GEMINI.md` Section 2.

### Q47. Why are synthetic identifiers used instead of real payment data?
- **SHORT ANSWER**: To prevent privacy violations, legal liability, and security breaches while fully demonstrating production architectural mechanics.
- **DEEP EXPLANATION**: Storing real card numbers requires PCI-DSS Level 1 physical HSMs and strict compliance audits. Using synthetic identifiers (`CUST-XXXX`, `DEV-XXXX`, tokenized hashes) allows full realistic simulation without risk.
- **WHERE IT APPEARS IN THIS PROJECT**: `docs/SECURITY.md` Section 2; `AGENTS.md` Rule 14.

### Q48. Why is "no fabricated metrics" a core rule of this project?
- **SHORT ANSWER**: Fabricating performance numbers defeats the educational and portfolio validity of the project; every metric must be measured on real held-out data.
- **DEEP EXPLANATION**: Anyone can write "PR-AUC = 0.99" in a markdown file. An engineering portfolio proves capability when metrics are generated via reproducible evaluation scripts (`ml/evaluate.py`) with transparent tradeoffs.
- **WHERE IT APPEARS IN THIS PROJECT**: `AGENTS.md` Rule 7 & 8; `docs/EXPERIMENTS.md`.

### Q49. What role does Docker Compose play in this architecture?
- **SHORT ANSWER**: It provides deterministic, reproducible local orchestration of all 11 heterogeneous services (Kafka, Redis, Postgres, ML, UI, Prometheus).
- **DEEP EXPLANATION**: A multi-technology distributed system is fragile if installed manually on developer machines. Docker Compose defines exact container images, networking, health checks, and volume mounts, allowing full bootup with a single command (`docker compose up`).
- **WHERE IT APPEARS IN THIS PROJECT**: `docker-compose.yml`; `docs/INFRASTRUCTURE.md`.

### Q50. How does Next.js 14 serve the fraud investigation persona?
- **SHORT ANSWER**: It renders a low-latency, real-time forensic dashboard with server-side rendered data, live WebSocket transaction streams, and client-side interactive SHAP waterfall plots.
- **DEEP EXPLANATION**: Fraud analysts need to make rapid triage decisions under time pressure. Next.js provides instant filtering, color-coded risk alerts, and deep-dive transaction forensic views without page reloads.
- **WHERE IT APPEARS IN THIS PROJECT**: `frontend/` directory; `docs/PRD.md` Persona 1.

### Q51. What is the Whiteboard Walkthrough of this complete platform?
- **SHORT ANSWER**: Incoming event $\to$ Kafka (`transactions.raw`) $\to$ Feature Service reads previous Redis state $\to$ Ingests into ML ensemble (XGBoost) $\to$ Calibrates probability $\to$ Evaluates Isolation Forest anomaly $\to$ Risk Engine applies rules and cost weights to produce 0–100 score $\to$ Decisions triaged into `APPROVE`/`REVIEW`/`BLOCK` $\to$ Durable audit in PostgreSQL $\to$ Visualized in Next.js with SHAP $\to$ Monitored in Prometheus/Grafana.
- **DEEP EXPLANATION**: The complete end-to-end integration proving systems engineering, applied machine learning, distributed state caching, and operational explainability.
- **WHERE IT APPEARS IN THIS PROJECT**: Master architecture diagram in `README.md` and `docs/ARCHITECTURE.md`.
