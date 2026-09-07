import React from 'react';
import { Card } from '../../../shared/components/Card';

export const RunningTradesSummary: React.FC = () => {
  return (
    <Card title="Running Orders Summary" subtitle="Live positions synced with MetaTrader 5">
      <div className="space-y-3">
        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
          <div>
            <span className="font-bold text-sm text-slate-200">EURUSD</span>
            <span className="ml-2 px-1.5 py-0.5 text-xs bg-emerald-950 text-emerald-400 rounded font-mono">BUY 0.05</span>
          </div>
          <div className="text-right">
            <span className="text-sm font-mono font-semibold text-emerald-400">+$32.50</span>
            <span className="block text-xs text-slate-400">SL: 1.0820 • TP: 1.0910</span>
          </div>
        </div>
        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
          <div>
            <span className="font-bold text-sm text-slate-200">GBPUSD</span>
            <span className="ml-2 px-1.5 py-0.5 text-xs bg-rose-950 text-rose-400 rounded font-mono">SELL 0.05</span>
          </div>
          <div className="text-right">
            <span className="text-sm font-mono font-semibold text-emerald-400">+$18.00</span>
            <span className="block text-xs text-slate-400">SL: 1.2750 • TP: 1.2640</span>
          </div>
        </div>
      </div>
    </Card>
  );
};
