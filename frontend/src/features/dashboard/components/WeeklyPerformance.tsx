import React from 'react';
import { Card } from '../../../shared/components/Card';

export const WeeklyPerformance: React.FC = () => {
  return (
    <Card title="Weekly Aggregation">
      <div className="grid grid-cols-2 gap-4 text-center">
        <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800">
          <span className="text-xs text-slate-400">Profit Factor</span>
          <p className="text-xl font-bold font-mono text-emerald-400 mt-1">2.45</p>
        </div>
        <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800">
          <span className="text-xs text-slate-400">Total Net PnL</span>
          <p className="text-xl font-bold font-mono text-emerald-400 mt-1">+$281.15</p>
        </div>
      </div>
    </Card>
  );
};
