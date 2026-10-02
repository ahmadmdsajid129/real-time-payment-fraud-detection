import React from 'react';
import { ShieldAlert, Activity, Database, Cpu, ExternalLink, Zap } from 'lucide-react';

export default function Navbar({ health, isStreaming }) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-gray-800 bg-[#0a0d14]/90 backdrop-blur-md px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-cyan-500 shadow-lg shadow-blue-500/20">
            <ShieldAlert className="w-5 h-5 text-white" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-lg font-bold tracking-tight text-white">AEGIS // RISK ENGINE</h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20">
                PROD v1.0.0
              </span>
            </div>
            <p className="text-xs text-gray-400 font-mono">Real-Time Payment Fraud Detection & Explainable AI</p>
          </div>
        </div>

        {/* System Health Indicators */}
        <div className="hidden md:flex items-center space-x-4">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 text-xs">
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-gray-400">Postgres:</span>
            <span className="font-mono text-emerald-400 font-medium">{health?.dependencies?.postgres || 'UP'}</span>
          </div>

          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 text-xs">
            <Zap className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-gray-400">Redis Cache:</span>
            <span className="font-mono text-cyan-400 font-medium">{health?.dependencies?.redis || 'UP'}</span>
          </div>

          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 text-xs">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-gray-400">Model:</span>
            <span className="font-mono text-indigo-300 font-medium">XGBoost+SHAP</span>
          </div>

          {/* External links */}
          <div className="flex items-center space-x-2 pl-2 border-l border-gray-800">
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              <span>Swagger</span>
              <ExternalLink className="w-3 h-3" />
            </a>
            <a
              href="http://localhost:8000/metrics"
              target="_blank"
              rel="noreferrer"
              className="flex items-center space-x-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              <span>Prometheus</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}
