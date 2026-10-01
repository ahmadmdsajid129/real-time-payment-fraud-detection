# Feature Engineering & Behavioral Analytics Specification

---

## 1. Feature Engineering Philosophy & Leakage Contract

Fraud detection accuracy hinges on behavioral context rather than raw transaction fields. 
However, computing behavioral context introduces extreme risks of **temporal data leakage**.

### The Zero-Leakage Contract
1. **Strict Temporal Precedence**: Any feature measuring customer behavior over a historical window $W = [t - \Delta, t)$ must only include transactions with timestamp $\tau < t$.
2. **Current Event Exclusion**: In online streaming, the Feature Service retrieves previous Redis state *before* updating Redis with the current transaction. In offline training, historical statistics are computed using rolling shift transformations (`df.groupby('customer_id')['amount'].shift(1)`).
3. **No Retrospective Normalization**: Global feature scalers (mean, standard deviation) fitted on the entire dataset leak future scale into the past. All transformers are fitted exclusively on the chronological training window.

---

## 2. Behavioral & Real-Time Feature Catalogue

| Feature Name | Definition & Formula | Window | Source | Risk Signal / Purpose | Leakage Safeguard |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `amount` | Transaction raw monetary amount | Point in time | Ingestion Payload | Baseline transaction magnitude. | N/A (Instant payload) |
| `log_amount` | $\ln(\text{amount} + 1)$ | Point in time | Computed | Compresses heavy-tailed financial distributions for linear/tree splits. | N/A |
| `customer_avg_amount` | $\mu_{\text{hist}} = \frac{1}{K}\sum_{i=1}^K x_i$ for past transactions | Lifetime / 30d | Redis / DB | Customer's historical spending baseline. | Computed strictly on events where $\tau < t$. |
| `customer_std_amount` | $\sigma_{\text{hist}} = \sqrt{\frac{1}{K}\sum (x_i - \mu)^2}$ | Lifetime / 30d | Redis / DB | Measure of customer spending volatility. | Computed strictly on events where $\tau < t$. |
| `customer_amount_zscore` | $\frac{\text{amount} - \mu_{\text{hist}}}{\sigma_{\text{hist}} + \epsilon}$ | Point vs. 30d | Computed | Detects high-value deviation from cardholder normal behavior. | Uses historical mean/std before current transaction. |
| `amount_to_avg_ratio` | $\frac{\text{amount}}{\mu_{\text{hist}} + 1.0}$ | Point vs. 30d | Computed | Scale-invariant ratio of current spend relative to normal basket. | Uses pre-transaction mean. |
| `time_since_prev_txn` | $t - t_{\text{prev}}$ (in seconds) | Event-to-event | Redis ZSET | Identifies rapid-fire automated card testing attacks. | Evaluated against last stored timestamp in Redis. |
| `txn_count_1m` | Count of transactions in $[t - 60s, t)$ | 1 Minute | Redis ZSET | Captures high-frequency automated bots / velocity spikes. | Sliding window strictly bounded at $t - 1\text{ms}$. |
| `txn_count_5m` | Count of transactions in $[t - 300s, t)$ | 5 Minutes | Redis ZSET | Rapid card testing before bank alerts trigger. | Excludes current transaction. |
| `txn_count_15m` | Count of transactions in $[t - 900s, t)$ | 15 Minutes | Redis ZSET | Sustained burst velocity attack. | Excludes current transaction. |
| `txn_count_1h` | Count of transactions in $[t - 3600s, t)$ | 1 Hour | Redis ZSET | Short-term velocity metric. | Excludes current transaction. |
| `txn_count_24h` | Count of transactions in $[t - 86400s, t)$ | 24 Hours | Redis ZSET | Daily frequency baseline comparison. | Excludes current transaction. |
| `txn_count_7d` | Count of transactions in 7 days | 7 Days | Redis / DB | Weekly customer activity baseline. | Excludes current transaction. |
| `amount_sum_5m` | $\sum \text{amount}_i$ in past 5m | 5 Minutes | Redis ZSET | Total monetary outflow in burst attack. | Excludes current transaction. |
| `amount_sum_1h` | $\sum \text{amount}_i$ in past 1h | 1 Hour | Redis ZSET | Total monetary drain in hour window. | Excludes current transaction. |
| `unique_merchants_24h` | $\vert \{ \text{merch}_i \} \vert$ in 24 hours | 24 Hours | Redis SADD | Detects card cycling across multiple merchants. | Excludes current merchant. |
| `unique_countries_7d` | $\vert \{ \text{country}_i \} \vert$ in 7 days | 7 Days | Redis SADD | Broad geographic dispersion indicator. | Evaluated prior to set insert. |
| `unique_devices_30d` | $\vert \{ \text{dev}_i \} \vert$ in 30 days | 30 Days | Redis SADD | Multiple device logins across account. | Evaluated prior to set insert. |
| `is_new_device` | $\mathbb{I}(\text{device\_id} \notin \text{KnownDevices})$ | 90 Days | Redis Set | Account takeover (ATO) indicator. | Membership checked before adding device. |
| `is_new_country` | $\mathbb{I}(\text{country} \notin \text{KnownCountries})$ | 90 Days | Redis Set | Card-not-present cross-border fraud flag. | Membership checked before adding country. |
| `is_new_city` | $\mathbb{I}(\text{city} \notin \text{KnownCities})$ | 90 Days | Redis Set | Domestic geographic deviation flag. | Membership checked before adding city. |
| `geo_distance_km` | Haversine distance from previous txn city | Event-to-event | Redis (Last Geo) | Spatial displacement from previous location. | Uses location of previous transaction. |
| `travel_speed_kmh` | $\frac{\text{geo\_distance\_km}}{(t - t_{\text{prev}}) / 3600}$ | Event-to-event | Computed | Physical travel velocity between locations. | Uses previous location and timestamp. |
| `impossible_travel` | $\mathbb{I}(\text{travel\_speed\_kmh} > 900)$ | Event-to-event | Computed | Physically impossible movement (e.g. NYC to London in 20m). | Strict temporal comparison. |
| `hour_of_day` | Hour in local customer timezone $[0, 23]$ | Point in time | Timestamp | Captures diurnal activity cycle. | Derived from event timestamp. |
| `day_of_week` | Day of week $[0, 6]$ | Point in time | Timestamp | Weekend vs. weekday spending habits. | Derived from event timestamp. |
| `is_weekend` | $\mathbb{I}(\text{day\_of\_week} \in \{5, 6\})$ | Point in time | Timestamp | Weekend risk variance. | Derived from event timestamp. |
| `is_unusual_hour` | $\mathbb{I}(\text{hour} < h_{\text{start}} \lor \text{hour} > h_{\text{end}})$ | Profile baseline | PostgreSQL / Redis | Late-night / off-hours activity for this customer. | Pre-configured customer diurnal profile. |
| `merchant_risk_tier` | Categorical risk rating (LOW, MED, HIGH) | Static / DB | PostgreSQL | Merchant category susceptibility to fraud (e.g., crypto, gaming). | Pre-aggregated offline merchant stats. |
| `device_customer_count` | Distinct customers using this device in 24h | 24 Hours | Redis Set | Device sharing / fraud ring credential testing. | Evaluated before adding current customer. |

---

## 3. Mathematical Formulations of Key Signals

### 3.1 Amount Z-Score
$$Z = \frac{x_t - \mu_{t-1}}{\sigma_{t-1} + \epsilon}$$
Where $\epsilon = 1.0$ prevents division by zero for customers with identical historical amounts. A $Z > 3.0$ indicates spending exceeding 3 standard deviations above their mean.

### 3.2 Impossible Travel Speed (Haversine Formulation)
$$d = 2R \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)} \right)$$
$$v = \frac{d}{\max((t - t_{\text{prev}}), 1) / 3600}$$
If $v > 900\text{ km/h}$ and $d > 200\text{ km}$, the `impossible_travel_indicator` is flagged as `1`.
