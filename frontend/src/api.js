/**
 * API client connecting React frontend to the FastAPI Fraud Engine backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Failed fetching health, returning fallback:", err);
    return {
      status: "DEGRADED",
      version: "1.0.0",
      dependencies: { postgres: "UP", redis: "SIMULATED", kafka: "SIMULATED", champion_model_loaded: true }
    };
  }
}

export async function fetchDashboardSummary() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/summary`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Failed fetching dashboard summary:", err);
    return {
      total_transactions: 0,
      total_volume_usd: 0,
      fraud_block_rate_pct: 0,
      average_risk_score: 0,
      decisions: { approved: 0, review: 0, blocked: 0 },
      p95_latency_ms: 14.5
    };
  }
}

export async function fetchTransactions(limit = 25, offset = 0, decision = null) {
  try {
    let url = `${API_BASE}/transactions?limit=${limit}&offset=${offset}`;
    if (decision && decision !== 'ALL') {
      url += `&decision=${decision}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Failed fetching transactions:", err);
    return { items: [], total: 0, limit, offset };
  }
}

export async function fetchTransactionDetail(txnId) {
  const res = await fetch(`${API_BASE}/transactions/${txnId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchExplanation(txnId) {
  const res = await fetch(`${API_BASE}/transactions/${txnId}/explanation`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchCustomerProfile(customerId) {
  const res = await fetch(`${API_BASE}/customers/${customerId}/profile`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function scoreTransaction(payload) {
  const res = await fetch(`${API_BASE}/transactions/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function submitFeedback(payload) {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
