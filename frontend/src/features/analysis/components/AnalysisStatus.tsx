import React from 'react';

export const AnalysisStatus: React.FC<{ symbol: string }> = ({ symbol }) => {
  return (
    <div className="flex items-center justify-between p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs">
      <span className="text-slate-400">Analysis Engine Context: <strong className="text-sky-400">{symbol}</strong></span>
      <span className="text-emerald-400 font-mono">Vol Regime: EXPANSION (1.62x)</span>
    </div>
  );
};
