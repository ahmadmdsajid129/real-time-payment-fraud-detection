import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, ShieldX, Search, Filter, Eye, ArrowUpRight, Smartphone, MapPin } from 'lucide-react';

export default function TransactionTable({ transactions, selectedTxn, onSelectTxn, activeFilter, onFilterChange }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = transactions.filter(t => {
    const matchesFilter = activeFilter === 'ALL' || t.decision === activeFilter;
    const matchesSearch = !searchTerm || 
      t.transaction_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.customer_id?.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getBadge = (decision) => {
    switch (decision) {
      case 'APPROVE':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-3 h-3 mr-1" /> APPROVE
          </span>
        );
      case 'REVIEW':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3 h-3 mr-1" /> REVIEW
          </span>
        );
      case 'BLOCK':
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20 animate-pulse-slow">
            <ShieldX className="w-3 h-3 mr-1" /> BLOCK
          </span>
        );
    }
  };

  const getScoreColor = (score) => {
    if (score < 30) return 'text-emerald-400';
    if (score < 75) return 'text-amber-400';
    return 'text-red-400 font-bold';
  };

  return (
    <div className="glass-panel rounded-2xl border border-gray-800 overflow-hidden shadow-xl">
      {/* Table Header / Filter controls */}
      <div className="p-4 border-b border-gray-800/80 flex flex-wrap items-center justify-between gap-3 bg-gray-900/40">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-bold text-white tracking-wide">Live Transaction Stream</span>
          <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-gray-800 text-gray-300">
            {filtered.length} events
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Search Bar */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-gray-500" />
            <input
              type="text"
              placeholder="Search TXN / Customer..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-lg bg-gray-950 border border-gray-800 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors w-48"
            />
          </div>

          {/* Decision Filter Tabs */}
          <div className="flex items-center p-0.5 rounded-lg bg-gray-950 border border-gray-800 text-xs font-medium">
            {['ALL', 'APPROVE', 'REVIEW', 'BLOCK'].map((f) => (
              <button
                key={f}
                onClick={() => onFilterChange(f)}
                className={`px-3 py-1 rounded-md transition-all ${
                  activeFilter === f
                    ? 'bg-blue-600 text-white font-semibold shadow-sm'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table body */}
      <div className="overflow-x-auto max-h-[520px] overflow-y-auto">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 z-10 bg-gray-950/90 backdrop-blur-sm border-b border-gray-800 text-gray-400 font-mono uppercase text-[11px]">
            <tr>
              <th className="py-3 px-4">Transaction ID</th>
              <th className="py-3 px-4">Customer</th>
              <th className="py-3 px-4">Amount</th>
              <th className="py-3 px-4">Risk Score</th>
              <th className="py-3 px-4">Decision</th>
              <th className="py-3 px-4">Location & Device</th>
              <th className="py-3 px-4">Latency</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60 font-mono">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan="8" className="py-12 text-center text-gray-500">
                  No transactions match the selected filter criteria.
                </td>
              </tr>
            ) : (
              filtered.map((t) => {
                const isSelected = selectedTxn?.transaction_id === t.transaction_id;
                const score = t.risk_score ?? (t.risk_decision?.risk_score ?? 0);
                const decision = t.decision ?? (t.risk_decision?.decision ?? 'APPROVE');
                const amount = (t.amount || 0).toLocaleString('en-US', {
                  style: 'currency',
                  currency: t.currency || 'USD'
                });
                const totalLatency = t.latency_breakdown_ms?.total || t.latency_ms || 18.2;

                return (
                  <tr
                    key={t.transaction_id}
                    onClick={() => onSelectTxn(t)}
                    className={`cursor-pointer transition-colors duration-150 ${
                      isSelected
                        ? 'bg-blue-600/10 border-l-2 border-blue-500'
                        : 'hover:bg-gray-800/40'
                    }`}
                  >
                    <td className="py-3 px-4 font-semibold text-gray-200">
                      <div className="flex items-center space-x-1.5">
                        <span className="truncate max-w-[130px]">{t.transaction_id}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-gray-400">{t.customer_id}</td>
                    <td className="py-3 px-4 font-bold text-white">{amount}</td>
                    <td className="py-3 px-4">
                      <span className={`font-bold ${getScoreColor(score)}`}>
                        {score.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-3 px-4">{getBadge(decision)}</td>
                    <td className="py-3 px-4 text-gray-400">
                      <div className="flex items-center space-x-2">
                        <span className="flex items-center space-x-1 text-gray-300">
                          <MapPin className="w-3 h-3 text-gray-500" />
                          <span>{t.city || t.country || 'US'}</span>
                        </span>
                        <span className="flex items-center space-x-1 text-gray-400">
                          <Smartphone className="w-3 h-3 text-gray-500" />
                          <span className="truncate max-w-[80px]">{t.device_id}</span>
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-gray-400 font-mono">
                      <span className="px-1.5 py-0.5 rounded bg-gray-900 border border-gray-800 text-[10px]">
                        {totalLatency.toFixed(1)}ms
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectTxn(t);
                        }}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md bg-gray-900 hover:bg-blue-600 hover:text-white border border-gray-700 text-gray-300 transition-colors text-[11px]"
                      >
                        <Eye className="w-3 h-3" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
