import React, { useState, useEffect } from 'react';
import { X, ShieldAlert, ShieldCheck, AlertTriangle, ArrowRight, UserCheck, CheckCircle2, Sliders, Activity, Info } from 'lucide-react';
import { fetchExplanation, fetchCustomerProfile, submitFeedback } from '../api';

export default function InspectorModal({ txn, onClose, onFeedbackSubmitted }) {
  const [explanation, setExplanation] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [feedbackLabel, setFeedbackLabel] = useState('FRAUD');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);

  useEffect(() => {
    if (!txn) return;
    let isMounted = true;
    setLoading(true);

    Promise.all([
      fetchExplanation(txn.transaction_id).catch(() => null),
      fetchCustomerProfile(txn.customer_id).catch(() => null)
    ]).then(([expData, profData]) => {
      if (!isMounted) return;
      setExplanation(expData);
      setProfile(profData);
      setLoading(false);
    });

    return () => { isMounted = false; };
  }, [txn]);

  if (!txn) return null;

  const score = txn.risk_score ?? (txn.risk_decision?.risk_score ?? 0);
  const decision = txn.decision ?? (txn.risk_decision?.decision ?? 'APPROVE');
  const calibratedProb = txn.calibrated_fraud_probability ?? (txn.prediction?.calibrated_probability ?? 0.05);
  const anomalyScore = txn.anomaly_score ?? (txn.prediction?.anomaly_score ?? 0.1);
  const rules = txn.rules_triggered ?? (txn.risk_decision?.rules_triggered ?? []);

  const positiveDrivers = explanation?.top_positive_drivers || txn.shap_positive_drivers || [];
  const negativeDrivers = explanation?.top_negative_drivers || txn.shap_negative_drivers || [];

  const handleFeedback = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await submitFeedback({
        transaction_id: txn.transaction_id,
        analyst_id: 'ANALYST-SEC-01',
        actual_label: feedbackLabel,
        notes: notes || undefined
      });
      setFeedbackSuccess(true);
      if (onFeedbackSubmitted) onFeedbackSubmitted();
      setTimeout(() => {
        setFeedbackSuccess(false);
        onClose();
      }, 1200);
    } catch (err) {
      alert(`Feedback submission failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto glass-panel-elevated rounded-3xl border border-gray-700/80 p-6 md:p-8 shadow-2xl text-gray-200">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 rounded-full bg-gray-900/80 hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-gray-800">
          <div>
            <div className="flex items-center space-x-3">
              <span className="text-xl font-bold font-mono text-white tracking-tight">
                {txn.transaction_id}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold font-mono ${
                  decision === 'APPROVE'
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    : decision === 'REVIEW'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    : 'bg-red-500/10 text-red-400 border border-red-500/30 animate-pulse'
                }`}
              >
                {decision}
              </span>
            </div>
            <p className="text-xs text-gray-400 font-mono mt-1">
              Customer: <span className="text-gray-200 font-semibold">{txn.customer_id}</span> • Device: <span className="text-gray-200">{txn.device_id}</span> • Location: <span className="text-gray-200">{txn.city || 'NYC'}, {txn.country || 'US'}</span>
            </p>
          </div>

          <div className="text-right">
            <div className="text-2xl font-bold font-mono text-white">
              {(txn.amount || 0).toLocaleString('en-US', { style: 'currency', currency: txn.currency || 'USD' })}
            </div>
            <div className="text-xs text-gray-400 font-mono">
              Risk Score: <span className="font-bold text-white text-sm">{score.toFixed(1)}</span> / 100
            </div>
          </div>
        </div>

        {/* Body Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          {/* Left Column: Multi-Factor Scoring & Rules */}
          <div className="space-y-6">
            {/* Multi-Factor Breakdown */}
            <div className="p-4 rounded-2xl bg-gray-950/60 border border-gray-800">
              <div className="flex items-center space-x-2 text-xs font-bold text-gray-300 uppercase tracking-wider mb-3">
                <Sliders className="w-4 h-4 text-blue-400" />
                <span>Multi-Factor Risk Synthesis</span>
              </div>
              
              <div className="space-y-3 text-xs font-mono">
                <div>
                  <div className="flex justify-between text-gray-400 mb-1">
                    <span>Calibrated ML Prob (55%)</span>
                    <span className="text-white font-bold">{(calibratedProb * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-900 rounded-full h-1.5">
                    <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${calibratedProb * 100}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-gray-400 mb-1">
                    <span>Isolation Forest Anomaly (15%)</span>
                    <span className="text-white font-bold">{(anomalyScore * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-900 rounded-full h-1.5">
                    <div className="bg-purple-500 h-1.5 rounded-full" style={{ width: `${anomalyScore * 100}%` }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-gray-400 mb-1">
                    <span>Composite Risk Score</span>
                    <span className={`font-bold ${score >= 75 ? 'text-red-400' : score >= 30 ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {score.toFixed(1)} / 100
                    </span>
                  </div>
                  <div className="w-full bg-gray-900 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500 h-2 rounded-full"
                      style={{ width: `${score}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Heuristic Rules Triggered */}
            <div className="p-4 rounded-2xl bg-gray-950/60 border border-gray-800">
              <div className="flex items-center space-x-2 text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <span>Deterministic Rules Triggered ({rules.length})</span>
              </div>
              {rules.length === 0 ? (
                <p className="text-xs text-gray-500 italic font-mono">No heuristic rules violated (Normal behavior).</p>
              ) : (
                <div className="space-y-1.5 mt-2">
                  {rules.map((rule, idx) => (
                    <div key={idx} className="flex items-center space-x-2 text-xs font-mono px-2.5 py-1.5 rounded-lg bg-red-950/30 border border-red-800/40 text-red-300">
                      <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                      <span>{rule}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Customer 360 Baseline */}
            <div className="p-4 rounded-2xl bg-gray-950/60 border border-gray-800">
              <div className="flex items-center space-x-2 text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">
                <UserCheck className="w-4 h-4 text-cyan-400" />
                <span>Customer 360 Baseline</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono mt-2">
                <div className="p-2 rounded bg-gray-900/60">
                  <span className="text-gray-400 block text-[10px]">Avg Spend:</span>
                  <span className="text-white font-bold">${(profile?.average_amount || 120.0).toFixed(2)}</span>
                </div>
                <div className="p-2 rounded bg-gray-900/60">
                  <span className="text-gray-400 block text-[10px]">Known Devices:</span>
                  <span className="text-white font-bold">{profile?.known_devices?.length || 1} registered</span>
                </div>
                <div className="p-2 rounded bg-gray-900/60">
                  <span className="text-gray-400 block text-[10px]">1-Hour Velocity:</span>
                  <span className="text-white font-bold">{profile?.recent_velocity?.txn_count_1h || 0} txns</span>
                </div>
                <div className="p-2 rounded bg-gray-900/60">
                  <span className="text-gray-400 block text-[10px]">24-Hour Velocity:</span>
                  <span className="text-white font-bold">{profile?.recent_velocity?.txn_count_24h || 1} txns</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: SHAP Local Explainability & Feedback */}
          <div className="space-y-6">
            {/* TreeSHAP Feature Attribution Waterfall */}
            <div className="p-4 rounded-2xl bg-gray-950/60 border border-gray-800">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-2 text-xs font-bold text-gray-300 uppercase tracking-wider">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  <span>TreeSHAP Local Drivers</span>
                </div>
                <span className="text-[10px] font-mono text-gray-500">Shapley Values</span>
              </div>

              {loading ? (
                <div className="py-8 text-center text-xs text-gray-500 font-mono animate-pulse">
                  Computing TreeSHAP feature attributions...
                </div>
              ) : (
                <div className="space-y-3 text-xs font-mono">
                  {/* Top positive (Risk Increasing) */}
                  <div>
                    <span className="text-[11px] font-semibold text-red-400 block mb-1.5">
                      Top Risk Increasers (+)
                    </span>
                    {positiveDrivers.length === 0 ? (
                      <p className="text-gray-500 text-[11px] italic">None</p>
                    ) : (
                      positiveDrivers.map((d, i) => (
                        <div key={i} className="flex items-center justify-between py-1 border-b border-gray-900">
                          <span className="text-gray-300 truncate max-w-[180px]">{d.feature}</span>
                          <span className="text-red-400 font-bold">+{d.shap_value.toFixed(4)}</span>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Top negative (Risk Reducing) */}
                  <div className="pt-2">
                    <span className="text-[11px] font-semibold text-emerald-400 block mb-1.5">
                      Top Risk Mitigators (-)
                    </span>
                    {negativeDrivers.length === 0 ? (
                      <p className="text-gray-500 text-[11px] italic">None</p>
                    ) : (
                      negativeDrivers.map((d, i) => (
                        <div key={i} className="flex items-center justify-between py-1 border-b border-gray-900">
                          <span className="text-gray-300 truncate max-w-[180px]">{d.feature}</span>
                          <span className="text-emerald-400 font-bold">{d.shap_value.toFixed(4)}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Analyst Feedback Form */}
            <div className="p-4 rounded-2xl bg-gray-950/60 border border-gray-800">
              <div className="flex items-center space-x-2 text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">
                <CheckCircle2 className="w-4 h-4 text-blue-400" />
                <span>Analyst Ground-Truth Triage</span>
              </div>
              <p className="text-[11px] text-gray-500 font-mono mb-3">
                Label transactions to feed continuous shadow model retraining.
              </p>

              {feedbackSuccess ? (
                <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/50 text-emerald-300 text-xs font-mono flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Feedback recorded into PostgreSQL successfully!</span>
                </div>
              ) : (
                <form onSubmit={handleFeedback} className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <label className="flex items-center space-x-1.5 text-xs text-red-400 font-mono cursor-pointer">
                      <input
                        type="radio"
                        name="label"
                        value="FRAUD"
                        checked={feedbackLabel === 'FRAUD'}
                        onChange={(e) => setFeedbackLabel(e.target.value)}
                        className="accent-red-500"
                      />
                      <span>Confirmed Fraud</span>
                    </label>

                    <label className="flex items-center space-x-1.5 text-xs text-emerald-400 font-mono cursor-pointer">
                      <input
                        type="radio"
                        name="label"
                        value="LEGITIMATE"
                        checked={feedbackLabel === 'LEGITIMATE'}
                        onChange={(e) => setFeedbackLabel(e.target.value)}
                        className="accent-emerald-500"
                      />
                      <span>Legitimate (FP)</span>
                    </label>
                  </div>

                  <input
                    type="text"
                    placeholder="Optional investigation notes (e.g. Card reported stolen)..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    maxLength={500}
                    className="w-full px-3 py-1.5 rounded-lg bg-gray-900 border border-gray-800 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 font-mono"
                  />

                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors disabled:opacity-50 font-mono"
                  >
                    {submitting ? 'Submitting...' : 'Submit Forensic Feedback'}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
