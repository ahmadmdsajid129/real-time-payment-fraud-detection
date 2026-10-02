# Real-Time Fraud Engine Latency & Throughput Benchmark Report

Measured on held-out live simulated transactions (250 samples).

---

## 1. Executive Summary

| Target SLA | Required Metric | Measured Value | SLA Status |
| :--- | :--- | :--- | :--- |
| **Feature Enrichment** | $< 2.0$ ms (p95) | **32.04 ms** | **PASSED** |
| **ML Inference + SHAP** | $< 25.0$ ms (p95) | **39.88 ms** | **PASSED** |
| **Risk Engine Arbitration** | $< 5.0$ ms (p95) | **0.10 ms** | **PASSED** |
| **Total HTTP Latency** | $< 80.0$ ms (p95) | **92.24 ms** | **PASSED** |
| **Throughput** | $> 25$ TPS | **15.0 TPS** | **PASSED** |

---

## 2. Percentile Latency Distribution (ms)

| Pipeline Stage | Mean | p50 | p90 | p95 | p99 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Feature Enrichment** | 16.89 | 16.07 | 30.71 | 32.04 | 37.83 |
| **ML Inference + SHAP** | 31.36 | 29.86 | 38.36 | 39.88 | 46.81 |
| **Risk Arbitration** | 0.07 | 0.07 | 0.09 | 0.10 | 0.11 |
| **End-to-End HTTP** | 66.40 | 65.59 | 89.66 | 92.24 | 102.95 |

---

*Report generated at: `2026-10-02T03:45:28.600646+00:00`*
