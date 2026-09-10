import React from 'react';
import { AnalysisStatusData } from '../types/analysis.types';

export const AnalysisStatus: React.FC<{ symbol: string; status: AnalysisStatusData | null }> = ({ symbol, status }) => {
  return (
    <div className="flex items-center justify-between p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs">
      <span className="text-slate-400">Analysis Engine Context: <strong className="text-sky-400">{symbol}</strong></span>
      {status?.hasData ? (
        <span className="text-emerald-400 font-mono">
          Vol Regime: {status.regime} {status.atr ? `(ATR: ${status.atr})` : ''}
        </span>
      ) : (
        <span className="text-slate-400 font-mono">
          Vol Regime: Standby (Awaiting Feed)
        </span>
      )}
    </div>
  );
};

