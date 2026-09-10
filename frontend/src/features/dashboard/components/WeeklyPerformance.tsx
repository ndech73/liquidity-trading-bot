import React from 'react';
import { Card } from '../../../shared/components/Card';
import { PerformanceDay } from '../types/dashboard.types';

export const WeeklyPerformance: React.FC<{ data?: PerformanceDay[] }> = ({ data = [] }) => {
  const netPnL = data.reduce((sum, d) => sum + d.pnl, 0);
  const totalTrades = data.reduce((sum, d) => sum + d.tradesCount, 0);

  return (
    <Card title="Weekly Aggregation">
      <div className="grid grid-cols-2 gap-4 text-center">
        <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800">
          <span className="text-xs text-slate-400">Total Trades</span>
          <p className="text-xl font-bold font-mono text-slate-200 mt-1">{totalTrades}</p>
        </div>
        <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800">
          <span className="text-xs text-slate-400">Weekly Net PnL</span>
          <p
            className={`text-xl font-bold font-mono mt-1 ${
              netPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {netPnL >= 0 ? `+$${netPnL.toFixed(2)}` : `-$${Math.abs(netPnL).toFixed(2)}`}
          </p>
        </div>
      </div>
    </Card>
  );
};
