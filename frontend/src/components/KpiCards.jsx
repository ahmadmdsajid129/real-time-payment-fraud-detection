import React from 'react';
import { DollarSign, ShieldCheck, AlertTriangle, ShieldX, Clock, TrendingUp } from 'lucide-react';

export default function KpiCards({ summary }) {
  const totalVolume = Number(summary?.total_volume_usd || 0).toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  });

  const totalTxns = Number(summary?.total_transactions || 0).toLocaleString();
  const blockRate = Number(summary?.fraud_block_rate_pct || 0).toFixed(2);
  const avgScore = Number(summary?.average_risk_score || 0).toFixed(1);
  const p95Latency = Number(summary?.p95_latency_ms || 14.5).toFixed(1);

  const approvedCount = summary?.decisions?.approved || 0;
  const reviewCount = summary?.decisions?.review || 0;
  const blockedCount = summary?.decisions?.blocked || 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* 1. Total Volume */}
      <div className="glass-panel rounded-2xl p-5 border border-gray-800/80 hover:border-blue-500/40 transition-all duration-300 shadow-lg">
        <div className="flex items-center justify-between text-gray-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Processed Volume</span>
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
            <DollarSign className="w-4 h-4" />
          </div>
        </div>
        <div className="text-2xl font-bold font-mono text-white tracking-tight">{totalVolume}</div>
        <div className="flex items-center space-x-1 mt-2 text-xs text-gray-400 font-mono">
          <span>{totalTxns} events evaluated</span>
        </div>
      </div>

      {/* 2. Fraud Block Rate */}
      <div className="glass-panel rounded-2xl p-5 border border-gray-800/80 hover:border-red-500/40 transition-all duration-300 shadow-lg">
        <div className="flex items-center justify-between text-gray-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Intercept Rate</span>
          <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
            <ShieldX className="w-4 h-4" />
          </div>
        </div>
        <div className="text-2xl font-bold font-mono text-red-400 tracking-tight">{blockRate}%</div>
        <div className="flex items-center justify-between mt-2 text-xs text-gray-400 font-mono">
          <span>Blocked: {blockedCount}</span>
          <span className="text-amber-400">Review: {reviewCount}</span>
        </div>
      </div>

      {/* 3. Approved Rate */}
      <div className="glass-panel rounded-2xl p-5 border border-gray-800/80 hover:border-emerald-500/40 transition-all duration-300 shadow-lg">
        <div className="flex items-center justify-between text-gray-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Instant Approval</span>
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
        </div>
        <div className="text-2xl font-bold font-mono text-emerald-400 tracking-tight">
          {approvedCount.toLocaleString()}
        </div>
        <div className="flex items-center space-x-1 mt-2 text-xs text-emerald-500/80 font-mono">
          <span>Score &lt; 30 (Frictionless)</span>
        </div>
      </div>

      {/* 4. Average Risk Score */}
      <div className="glass-panel rounded-2xl p-5 border border-gray-800/80 hover:border-amber-500/40 transition-all duration-300 shadow-lg">
        <div className="flex items-center justify-between text-gray-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">Mean Risk Score</span>
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <TrendingUp className="w-4 h-4" />
          </div>
        </div>
        <div className="text-2xl font-bold font-mono text-white tracking-tight">
          {avgScore} <span className="text-xs text-gray-500 font-normal">/ 100</span>
        </div>
        <div className="w-full bg-gray-800 rounded-full h-1.5 mt-3">
          <div
            className="bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500 h-1.5 rounded-full"
            style={{ width: `${Math.min(100, Math.max(0, avgScore))}%` }}
          ></div>
        </div>
      </div>

      {/* 5. Latency SLA */}
      <div className="glass-panel rounded-2xl p-5 border border-gray-800/80 hover:border-cyan-500/40 transition-all duration-300 shadow-lg">
        <div className="flex items-center justify-between text-gray-400 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider">p95 Latency</span>
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
            <Clock className="w-4 h-4" />
          </div>
        </div>
        <div className="text-2xl font-bold font-mono text-cyan-400 tracking-tight">
          {p95Latency} <span className="text-xs text-gray-400">ms</span>
        </div>
        <div className="flex items-center space-x-1 mt-2 text-xs text-cyan-400/80 font-mono">
          <span>Target SLA: &lt; 80ms</span>
        </div>
      </div>
    </div>
  );
}
