import React, { useState } from 'react';
import { Play, Pause, Zap, Coffee, FastForward, Globe, AlertOctagon, RotateCw } from 'lucide-react';

export default function SimulatorBar({ onInject, isAutoStreaming, onToggleAutoStream, isSimulating }) {
  const [activeScenario, setActiveScenario] = useState(null);

  const handleScenario = async (type) => {
    setActiveScenario(type);
    await onInject(type);
    setTimeout(() => setActiveScenario(null), 800);
  };

  return (
    <div className="glass-panel rounded-2xl p-4 border border-gray-800 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center space-x-2">
        <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
          <Zap className="w-4 h-4" />
        </div>
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-gray-300">Live Attack Simulator</span>
          <p className="text-xs text-gray-500">Inject synthetic payment vectors into scoring pipeline</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {/* Normal Coffee */}
        <button
          onClick={() => handleScenario('normal')}
          disabled={isSimulating}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-900 border border-emerald-500/30 text-emerald-400 text-xs font-medium hover:bg-emerald-500/10 hover:border-emerald-500 transition-all disabled:opacity-50"
        >
          <Coffee className="w-3.5 h-3.5" />
          <span>Normal Spend ($4.50)</span>
        </button>

        {/* Velocity Burst */}
        <button
          onClick={() => handleScenario('velocity')}
          disabled={isSimulating}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-900 border border-amber-500/30 text-amber-400 text-xs font-medium hover:bg-amber-500/10 hover:border-amber-500 transition-all disabled:opacity-50"
        >
          <FastForward className="w-3.5 h-3.5" />
          <span>Velocity Burst (5x)</span>
        </button>

        {/* Impossible Travel */}
        <button
          onClick={() => handleScenario('travel')}
          disabled={isSimulating}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-900 border border-blue-500/30 text-blue-400 text-xs font-medium hover:bg-blue-500/10 hover:border-blue-500 transition-all disabled:opacity-50"
        >
          <Globe className="w-3.5 h-3.5" />
          <span>Impossible Travel (NYC→TYO)</span>
        </button>

        {/* Account Takeover */}
        <button
          onClick={() => handleScenario('ato')}
          disabled={isSimulating}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-900 border border-red-500/30 text-red-400 text-xs font-medium hover:bg-red-500/10 hover:border-red-500 transition-all disabled:opacity-50"
        >
          <AlertOctagon className="w-3.5 h-3.5" />
          <span>Account Takeover ($9,450)</span>
        </button>

        {/* Auto Stream Play/Pause */}
        <button
          onClick={onToggleAutoStream}
          className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-md transition-all ${
            isAutoStreaming
              ? 'bg-red-600/20 text-red-400 border border-red-500/40 hover:bg-red-600/30'
              : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-indigo-600/30'
          }`}
        >
          {isAutoStreaming ? (
            <>
              <Pause className="w-3.5 h-3.5" />
              <span>Pause Stream</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5" />
              <span>Auto Stream (2s)</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
