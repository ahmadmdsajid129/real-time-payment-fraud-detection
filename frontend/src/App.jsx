import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import KpiCards from './components/KpiCards';
import SimulatorBar from './components/SimulatorBar';
import TransactionTable from './components/TransactionTable';
import InspectorModal from './components/InspectorModal';
import { fetchHealth, fetchDashboardSummary, fetchTransactions, scoreTransaction } from './api';

export default function App() {
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [selectedTxn, setSelectedTxn] = useState(null);
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [isAutoStreaming, setIsAutoStreaming] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const streamTimerRef = useRef(null);

  // Initial load & Polling
  const refreshData = async () => {
    try {
      const [h, s, t] = await Promise.all([
        fetchHealth(),
        fetchDashboardSummary(),
        fetchTransactions(30, 0, activeFilter)
      ]);
      setHealth(h);
      setSummary(s);
      if (Array.isArray(t)) {
        setTransactions(prev => {
          // Deduplicate and merge database transactions with recent live in-flight events
          const fetchedIds = new Set(t.map(item => item.transaction_id));
          const recentInFlight = prev.filter(item => !fetchedIds.has(item.transaction_id));
          return [...recentInFlight, ...t].slice(0, 30);
        });
      }
    } catch (err) {
      console.warn("Polling error:", err);
    }
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 4000);
    return () => clearInterval(interval);
  }, [activeFilter]);

  // Scenario Injection Handlers
  const handleInjectScenario = async (scenarioType) => {
    setIsSimulating(true);
    const now = new Date().toISOString();
    const nonce = Math.floor(Math.random() * 10000);

    let payload;
    switch (scenarioType) {
      case 'velocity':
        // Fire 4 rapid micro-transactions
        for (let i = 1; i <= 4; i++) {
          await scoreTransaction({
            transaction_id: `TXN-BURST-${Date.now()}-${i}`,
            customer_id: 'CUST-BURST-01',
            amount: 12.50,
            currency: 'USD',
            country: 'US',
            city: 'Chicago',
            device_id: 'DEV-BURST-MOBILE',
            payment_method: 'credit_card',
            idempotency_key: `idemp-burst-${Date.now()}-${i}`
          }).catch(() => {});
        }
        payload = {
          transaction_id: `TXN-BURST-${Date.now()}-5`,
          customer_id: 'CUST-BURST-01',
          amount: 145.00,
          currency: 'USD',
          country: 'US',
          city: 'Chicago',
          device_id: 'DEV-BURST-MOBILE',
          payment_method: 'credit_card',
          idempotency_key: `idemp-burst-${Date.now()}-5`
        };
        break;

      case 'travel':
        payload = {
          transaction_id: `TXN-TRAVEL-${Date.now()}`,
          customer_id: 'CUST-EXP-088',
          amount: 850.00,
          currency: 'USD',
          country: 'JP',
          city: 'Tokyo',
          lat: 35.6762,
          lon: 139.6503,
          device_id: 'DEV-JP-PROXY-01',
          payment_method: 'credit_card',
          idempotency_key: `idemp-travel-${Date.now()}`
        };
        break;

      case 'ato':
        payload = {
          transaction_id: `TXN-ATO-${Date.now()}`,
          customer_id: 'CUST-LEGIT-500',
          amount: 9450.00,
          currency: 'USD',
          country: 'US',
          city: 'Miami',
          device_id: 'DEV-NEW-UNKNOWN-X',
          payment_method: 'credit_card',
          idempotency_key: `idemp-ato-${Date.now()}`
        };
        break;

      case 'normal':
      default:
        payload = {
          transaction_id: `TXN-NORM-${Date.now()}`,
          customer_id: `CUST-${100 + (nonce % 20)}`,
          amount: parseFloat((Math.random() * 25 + 3.5).toFixed(2)),
          currency: 'USD',
          country: 'US',
          city: 'New York',
          lat: 40.7128,
          lon: -74.0060,
          device_id: 'DEV-USER-IPHONE',
          payment_method: 'credit_card',
          idempotency_key: `idemp-norm-${Date.now()}`
        };
        break;
    }

    try {
      const scored = await scoreTransaction(payload);
      // Merge payload attributes (amount, customer_id, location, device) with scoring outputs
      const completeTxn = {
        ...payload,
        ...scored,
        latency_ms: scored.latency_breakdown_ms?.total || 18.0
      };
      setTransactions(prev => [completeTxn, ...prev.filter(x => x.transaction_id !== completeTxn.transaction_id)].slice(0, 30));
      // Trigger background summary refresh
      fetchDashboardSummary().then(setSummary).catch(() => {});
    } catch (err) {
      console.error("Scenario execution error:", err);
    } finally {
      setIsSimulating(false);
    }
  };

  // Auto-stream loop
  const toggleAutoStream = () => {
    if (isAutoStreaming) {
      clearInterval(streamTimerRef.current);
      setIsAutoStreaming(false);
    } else {
      setIsAutoStreaming(true);
      streamTimerRef.current = setInterval(() => {
        const scenarios = ['normal', 'normal', 'normal', 'velocity', 'travel'];
        const chosen = scenarios[Math.floor(Math.random() * scenarios.length)];
        handleInjectScenario(chosen);
      }, 2500);
    }
  };

  useEffect(() => {
    return () => {
      if (streamTimerRef.current) clearInterval(streamTimerRef.current);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#080b11] text-gray-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Navigation */}
      <Navbar health={health} isStreaming={isAutoStreaming} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* KPI Metrics Summary */}
        <KpiCards summary={summary} />

        {/* Live Attack Simulator Toolbar */}
        <SimulatorBar
          onInject={handleInjectScenario}
          isAutoStreaming={isAutoStreaming}
          onToggleAutoStream={toggleAutoStream}
          isSimulating={isSimulating}
        />

        {/* Live Transaction Feed Table */}
        <TransactionTable
          transactions={transactions}
          selectedTxn={selectedTxn}
          onSelectTxn={setSelectedTxn}
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
        />
      </main>

      {/* Deep-Dive Inspection Modal */}
      {selectedTxn && (
        <InspectorModal
          txn={selectedTxn}
          onClose={() => setSelectedTxn(null)}
          onFeedbackSubmitted={refreshData}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-gray-900 bg-[#06080d] py-4 text-center text-xs text-gray-500 font-mono">
        <p>AegisRisk Engine • Calibrated XGBoost + TreeSHAP + Isolation Forest + Redis Sliding State • Sub-80ms p95</p>
      </footer>
    </div>
  );
}
