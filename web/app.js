/**
 * Real-Time Payment Fraud Detection & Risk Engine
 * Frontend Client Application & Interactive Dashboard Logic
 */

const API_BASE = "http://localhost:8000/api/v1";

// State
let allTransactions = [];
let activeFilter = "ALL";
let isLiveStreaming = false;
let streamInterval = null;
let currentInspectedTxnId = null;

// DOM Elements
const kpiTotalVolume = document.getElementById("kpi-total-volume");
const kpiTotalTxns = document.getElementById("kpi-total-txns");
const kpiBlockRate = document.getElementById("kpi-block-rate");
const kpiBlockedCount = document.getElementById("kpi-blocked-count");
const kpiReviewQueue = document.getElementById("kpi-review-queue");
const kpiAvgScore = document.getElementById("kpi-avg-score");
const tableBody = document.getElementById("transactions-body");
const btnSimulate = document.getElementById("btn-simulate");
const btnToggleStream = document.getElementById("btn-toggle-stream");
const scenarioSelect = document.getElementById("scenario-select");
const modal = document.getElementById("investigation-modal");
const modalCloseBtn = document.getElementById("modal-close-btn");

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  fetchHealth();
  fetchSummary();
  fetchRecentTransactions();
  fetchRiskDistribution();
});

function setupEventListeners() {
  // Filters
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeFilter = btn.dataset.filter;
      renderTable();
    });
  });

  // Simulator
  btnSimulate.addEventListener("click", () => {
    triggerSimulatedTransaction(scenarioSelect.value);
  });

  // Live Stream Toggle
  btnToggleStream.addEventListener("click", toggleLiveStream);

  // Modal Close
  modalCloseBtn.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  // Analyst Action Buttons
  document.getElementById("btn-submit-legit").addEventListener("click", () => submitFeedback("LEGITIMATE"));
  document.getElementById("btn-submit-fraud").addEventListener("click", () => submitFeedback("FRAUD"));
}

// -----------------------------------------------------------------------------
// API Calls
// -----------------------------------------------------------------------------
async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    const data = await res.json();
    const statusText = document.getElementById("system-status-text");
    if (data.status === "HEALTHY") {
      statusText.textContent = `SYSTEM ONLINE (${data.dependencies.postgres === "UP" ? "PG UP" : "SQLITE ACTIVE"}, REDIS READY)`;
    } else {
      statusText.textContent = "SYSTEM DEGRADED";
    }
  } catch (err) {
    document.getElementById("system-status-text").textContent = "DISCONNECTED (STANDALONE DEMO MODE)";
  }
}

async function fetchSummary() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/summary`);
    const data = await res.json();
    kpiTotalVolume.textContent = `$${data.total_volume_usd.toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
    kpiTotalTxns.textContent = `${data.total_transactions} transactions`;
    kpiBlockRate.textContent = `${data.fraud_block_rate_pct}%`;
    kpiBlockedCount.textContent = `${data.decisions.blocked} blocked transactions`;
    kpiReviewQueue.textContent = data.decisions.review;
    kpiAvgScore.textContent = data.average_risk_score;
  } catch (err) {
    console.warn("Could not fetch summary:", err);
  }
}

async function fetchRecentTransactions() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/recent-transactions?limit=25`);
    const data = await res.json();
    if (Array.isArray(data) && data.length > 0) {
      allTransactions = data;
      renderTable();
    } else {
      // Seed with initial realistic demo transactions if empty
      allTransactions = getSeedTransactions();
      renderTable();
    }
  } catch (err) {
    allTransactions = getSeedTransactions();
    renderTable();
  }
}

async function fetchRiskDistribution() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/risk-distribution`);
    const buckets = await res.json();
    drawHistogram(buckets);
  } catch (err) {
    drawHistogram([
      { bucket: "0-10", count: 420 },
      { bucket: "10-20", count: 210 },
      { bucket: "20-30", count: 95 },
      { bucket: "30-40", count: 32 },
      { bucket: "40-50", count: 18 },
      { bucket: "50-60", count: 12 },
      { bucket: "60-70", count: 8 },
      { bucket: "70-80", count: 15 },
      { bucket: "80-90", count: 24 },
      { bucket: "90-100", count: 38 },
    ]);
  }
}

// -----------------------------------------------------------------------------
// Transaction Rendering
// -----------------------------------------------------------------------------
function renderTable() {
  tableBody.innerHTML = "";
  const filtered = activeFilter === "ALL" 
    ? allTransactions 
    : allTransactions.filter((t) => t.decision === activeFilter);

  if (filtered.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-dim); padding: 2rem;">No transactions matching filter "${activeFilter}"</td></tr>`;
    return;
  }

  filtered.forEach((txn) => {
    const row = document.createElement("tr");

    const badgeClass = txn.decision === "APPROVE" 
      ? "badge-approve" 
      : txn.decision === "REVIEW" 
        ? "badge-review" 
        : "badge-block";

    const score = Number(txn.risk_score || 0);
    const scoreColor = score < 30 ? "var(--status-approve)" : score < 75 ? "var(--status-review)" : "var(--status-block)";

    const timeFormatted = txn.timestamp 
      ? new Date(txn.timestamp).toLocaleTimeString() 
      : new Date().toLocaleTimeString();

    row.innerHTML = `
      <td class="mono-cell">${timeFormatted}</td>
      <td class="mono-cell" style="font-weight: 600; color: #fff;">${txn.transaction_id}</td>
      <td class="mono-cell">${txn.customer_id}</td>
      <td style="font-weight: 600; color: #fff;">$${Number(txn.amount).toFixed(2)}</td>
      <td>${txn.country} · ${txn.city}</td>
      <td><span class="badge ${badgeClass}">${txn.decision}</span></td>
      <td>
        <div class="risk-meter">
          <div class="risk-bar">
            <div class="risk-fill" style="width: ${Math.min(100, Math.max(0, score))}%; background: ${scoreColor};"></div>
          </div>
          <span style="font-family: var(--font-mono); font-size: 0.8rem; color: ${scoreColor}; font-weight: 600;">${score.toFixed(1)}</span>
        </div>
      </td>
      <td>
        <button class="btn-inspect" onclick="openInspector('${txn.transaction_id}')">Audit 🔍</button>
      </td>
    `;
    tableBody.appendChild(row);
  });
}

// -----------------------------------------------------------------------------
// Interactive Simulation & Live Stream
// -----------------------------------------------------------------------------
async function triggerSimulatedTransaction(scenario = "normal") {
  const custId = `CUST-${Math.floor(1000 + Math.random() * 9000)}`;
  const txnId = `TXN-${Math.floor(100000 + Math.random() * 900000)}`;

  let payload = {
    transaction_id: txnId,
    timestamp: new Date().toISOString(),
    customer_id: custId,
    merchant_id: "MERCH-4091",
    amount: 85.00,
    currency: "USD",
    country: "US",
    city: "New York",
    lat: 40.7128,
    lon: -74.0060,
    device_id: "DEV-MOBILE-01",
    payment_method: "credit_card",
    ip_address: "192.168.1.1",
    idempotency_key: `idemp-${txnId}`,
  };

  if (scenario === "velocity_spike") {
    payload.amount = 450.00;
  } else if (scenario === "impossible_travel") {
    payload.amount = 320.00;
    payload.country = "SG";
    payload.city = "Singapore";
    payload.lat = 1.3521;
    payload.lon = 103.8198;
  } else if (scenario === "account_takeover") {
    payload.amount = 3200.00;
    payload.device_id = "DEV-UNKNOWN-SYNDICATE";
    payload.country = "RU";
    payload.city = "Moscow";
  } else if (scenario === "luxury_burst") {
    payload.amount = 9500.00;
    payload.merchant_category = "JEWELRY_LUXURY";
  }

  try {
    const res = await fetch(`${API_BASE}/transactions/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await res.json();

    const newTxn = {
      transaction_id: result.transaction_id,
      timestamp: result.evaluated_at,
      customer_id: custId,
      amount: payload.amount,
      country: payload.country,
      city: payload.city,
      decision: result.decision,
      risk_score: result.risk_score,
      calibrated_probability: result.calibrated_fraud_probability,
      anomaly_score: result.anomaly_score,
      triggered_rules: result.triggered_rules,
    };

    allTransactions.unshift(newTxn);
    if (allTransactions.length > 50) allTransactions.pop();
    renderTable();
    fetchSummary();
  } catch (err) {
    console.warn("API scoring failed, appending fallback simulated record:", err);
  }
}

function toggleLiveStream() {
  isLiveStreaming = !isLiveStreaming;
  if (isLiveStreaming) {
    btnToggleStream.textContent = "⏸ Pause Live Feed";
    btnToggleStream.style.borderColor = "var(--status-review)";
    btnToggleStream.style.color = "var(--status-review)";
    streamInterval = setInterval(() => {
      const scenarios = ["normal", "normal", "normal", "velocity_spike", "impossible_travel", "account_takeover"];
      const randomScenario = scenarios[Math.floor(Math.random() * scenarios.length)];
      triggerSimulatedTransaction(randomScenario);
    }, 2500);
  } else {
    btnToggleStream.textContent = "▶ Start Live Feed";
    btnToggleStream.style.borderColor = "";
    btnToggleStream.style.color = "";
    clearInterval(streamInterval);
  }
}

// -----------------------------------------------------------------------------
// Forensic Inspector Modal & SHAP Waterfall
// -----------------------------------------------------------------------------
window.openInspector = async function(txnId) {
  currentInspectedTxnId = txnId;
  const txn = allTransactions.find((t) => t.transaction_id === txnId);
  if (!txn) return;

  document.getElementById("modal-txn-id").textContent = txn.transaction_id;
  document.getElementById("modal-meta-info").textContent = `Customer: ${txn.customer_id} | Amount: $${Number(txn.amount).toFixed(2)} | Location: ${txn.country || "US"}`;

  const badgeEl = document.getElementById("modal-decision-badge");
  const badgeClass = txn.decision === "APPROVE" ? "badge-approve" : txn.decision === "REVIEW" ? "badge-review" : "badge-block";
  badgeEl.innerHTML = `<span class="badge ${badgeClass}" style="font-size: 0.85rem; padding: 0.35rem 0.85rem;">${txn.decision} (${Number(txn.risk_score).toFixed(1)})</span>`;

  // Signals
  document.getElementById("modal-signal-ml").textContent = `${((txn.calibrated_probability || 0.05) * 100).toFixed(1)}%`;
  document.getElementById("modal-signal-anom").textContent = Number(txn.anomaly_score || 0.1).toFixed(2);
  document.getElementById("modal-signal-behav").textContent = (Number(txn.risk_score || 20) / 100).toFixed(2);

  // Triggered Rules
  const rulesList = document.getElementById("modal-rules-list");
  rulesList.innerHTML = "";
  const rules = txn.triggered_rules || [];
  document.getElementById("modal-signal-rules").textContent = rules.length;

  if (rules.length === 0) {
    rulesList.innerHTML = `<span style="font-size: 0.82rem; color: var(--text-dim);">No rules triggered. Clean transaction history.</span>`;
  } else {
    rules.forEach((r) => {
      const ruleName = typeof r === "string" ? r : r.name || r.rule_id;
      const tag = document.createElement("span");
      tag.style.cssText = "background: rgba(244, 63, 94, 0.15); border: 1px solid rgba(244, 63, 94, 0.4); color: #f43f5e; padding: 0.3rem 0.6rem; border-radius: 6px; font-size: 0.78rem; font-family: var(--font-mono);";
      tag.textContent = `🚨 ${ruleName}`;
      rulesList.appendChild(tag);
    });
  }

  // SHAP Waterfall
  const shapContainer = document.getElementById("modal-shap-container");
  shapContainer.innerHTML = "";

  try {
    const res = await fetch(`${API_BASE}/transactions/${txnId}/explanation`);
    const expl = await res.json();
    renderShapBars(shapContainer, expl.top_positive_features || [], expl.top_negative_features || []);
  } catch (err) {
    renderShapBars(shapContainer, [
      { feature: "amount_to_avg_ratio", impact: 0.34 },
      { feature: "travel_speed_kmh", impact: 0.22 },
      { feature: "txn_count_1h", impact: 0.15 },
    ], [
      { feature: "customer_age_days", impact: -0.05 },
      { feature: "is_common_channel", impact: -0.02 },
    ]);
  }

  // Customer Baseline Profile
  const custInfo = document.getElementById("modal-customer-info");
  try {
    const res = await fetch(`${API_BASE}/customers/${txn.customer_id}/profile`);
    const prof = await res.json();
    custInfo.innerHTML = `
      <div><span style="color: var(--text-dim);">Home Country:</span> <strong>${prof.home_country}</strong></div>
      <div><span style="color: var(--text-dim);">Historical Avg:</span> <strong>$${prof.historical_average_amount.toFixed(2)}</strong></div>
      <div><span style="color: var(--text-dim);">Risk Tier:</span> <strong>${prof.risk_tier}</strong></div>
      <div><span style="color: var(--text-dim);">Txns (24h):</span> <strong>${prof.recent_velocity.count_last_24h}</strong></div>
      <div><span style="color: var(--text-dim);">Known Devices:</span> <strong>${prof.known_devices.length} registered</strong></div>
      <div><span style="color: var(--text-dim);">Known Countries:</span> <strong>${prof.known_countries.join(", ")}</strong></div>
    `;
  } catch (err) {
    custInfo.innerHTML = `
      <div><span style="color: var(--text-dim);">Historical Avg:</span> <strong>$125.00</strong></div>
      <div><span style="color: var(--text-dim);">Known Devices:</span> <strong>1 (DEV-MOBILE-01)</strong></div>
      <div><span style="color: var(--text-dim);">Risk Tier:</span> <strong>STANDARD</strong></div>
    `;
  }

  modal.classList.add("active");
};

function renderShapBars(container, positiveDrivers, negativeDrivers) {
  positiveDrivers.forEach((d) => {
    const widthPct = Math.min(100, Math.max(10, Math.abs(d.impact) * 200));
    const row = document.createElement("div");
    row.className = "shap-bar-row";
    row.innerHTML = `
      <div class="shap-feature-name" title="${d.feature}">${d.feature}</div>
      <div class="shap-bar-track">
        <div class="shap-bar-fill-pos" style="width: ${widthPct}%;"></div>
      </div>
      <div class="shap-val" style="color: #f43f5e;">+${d.impact.toFixed(3)}</div>
    `;
    container.appendChild(row);
  });

  negativeDrivers.forEach((d) => {
    const widthPct = Math.min(100, Math.max(10, Math.abs(d.impact) * 200));
    const row = document.createElement("div");
    row.className = "shap-bar-row";
    row.innerHTML = `
      <div class="shap-feature-name" title="${d.feature}">${d.feature}</div>
      <div class="shap-bar-track">
        <div class="shap-bar-fill-neg" style="width: ${widthPct}%;"></div>
      </div>
      <div class="shap-val" style="color: #10b981;">${d.impact.toFixed(3)}</div>
    `;
    container.appendChild(row);
  });
}

function closeModal() {
  modal.classList.remove("active");
  document.getElementById("analyst-feedback-alert").style.display = "none";
}

async function submitFeedback(label) {
  if (!currentInspectedTxnId) return;
  const notes = document.getElementById("analyst-notes").value;
  const alertBox = document.getElementById("analyst-feedback-alert");

  try {
    const res = await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transaction_id: currentInspectedTxnId,
        analyst_id: "ANALYST-CHIEF-01",
        actual_label: label,
        notes: notes || "Review completed via forensic inspector.",
      }),
    });
    if (res.ok) {
      alertBox.style.display = "block";
      alertBox.style.color = "var(--status-approve)";
      alertBox.textContent = `✓ Feedback saved: Marked as ${label}. Ground-truth label stored in database.`;
    }
  } catch (err) {
    alertBox.style.display = "block";
    alertBox.style.color = "var(--status-approve)";
    alertBox.textContent = `✓ Simulated feedback recorded: Marked as ${label}.`;
  }
}

// -----------------------------------------------------------------------------
// Canvas Risk Histogram Renderer
// -----------------------------------------------------------------------------
function drawHistogram(buckets) {
  const canvas = document.getElementById("risk-chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  const maxCount = Math.max(...buckets.map((b) => b.count), 1);
  const barWidth = (width - 60) / buckets.length;
  const chartHeight = height - 50;

  buckets.forEach((b, i) => {
    const barH = (b.count / maxCount) * chartHeight;
    const x = 40 + i * barWidth;
    const y = height - 30 - barH;

    // Color gradient based on risk zone
    let color = "#10b981"; // Approve
    if (i >= 3 && i < 7) color = "#f59e0b"; // Review
    if (i >= 7) color = "#f43f5e"; // Block

    ctx.fillStyle = color;
    ctx.fillRect(x + 2, y, barWidth - 4, barH);

    // Labels
    ctx.fillStyle = "#64748b";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "center";
    if (i % 2 === 0) {
      ctx.fillText(b.bucket.split("-")[0], x + barWidth / 2, height - 12);
    }
  });
}

function getSeedTransactions() {
  return [
    {
      transaction_id: "TXN-883921",
      timestamp: new Date().toISOString(),
      customer_id: "CUST-1049",
      amount: 4500.0,
      country: "SG",
      city: "Singapore",
      decision: "BLOCK",
      risk_score: 89.4,
      calibrated_probability: 0.865,
      anomaly_score: 0.78,
      triggered_rules: ["IMPOSSIBLE_TRAVEL", "UNRECOGNIZED_DEVICE"],
    },
    {
      transaction_id: "TXN-883920",
      timestamp: new Date(Date.now() - 45000).toISOString(),
      customer_id: "CUST-4021",
      amount: 480.0,
      country: "US",
      city: "Chicago",
      decision: "REVIEW",
      risk_score: 54.2,
      calibrated_probability: 0.38,
      anomaly_score: 0.42,
      triggered_rules: ["VELOCITY_BURST_1H"],
    },
    {
      transaction_id: "TXN-883919",
      timestamp: new Date(Date.now() - 120000).toISOString(),
      customer_id: "CUST-9012",
      amount: 42.5,
      country: "US",
      city: "New York",
      decision: "APPROVE",
      risk_score: 8.5,
      calibrated_probability: 0.02,
      anomaly_score: 0.05,
      triggered_rules: [],
    },
  ];
}
