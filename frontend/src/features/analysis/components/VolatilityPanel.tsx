import React from 'react';
import { Card } from '../../../shared/components/Card';

export const VolatilityPanel: React.FC = () => {
  return (
    <Card title="Volatility Regime & Compression">
      <div className="grid grid-cols-2 gap-3 text-center text-xs">
        <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
          <span className="text-slate-400">Compression Ratio</span>
          <p className="text-lg font-mono font-bold text-sky-400 mt-1">0.64</p>
          <span className="text-emerald-400 text-xs">Below threshold (0.70)</span>
        </div>
        <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
          <span className="text-slate-400">Expansion Multiplier</span>
          <p className="text-lg font-mono font-bold text-emerald-400 mt-1">1.62x</p>
          <span className="text-emerald-400 text-xs">Breakout Validated</span>
        </div>
      </div>
    </Card>
  );
};
