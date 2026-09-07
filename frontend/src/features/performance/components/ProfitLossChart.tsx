import React from 'react';
import { Card } from '../../../shared/components/Card';

export const ProfitLossChart: React.FC = () => {
  return (
    <Card title="Profit / Loss Ratio">
      <div className="space-y-3 text-xs">
        <div className="flex justify-between">
          <span className="text-slate-400">Average Win:</span>
          <span className="font-mono text-emerald-400 font-bold">+$48.20</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Average Loss:</span>
          <span className="font-mono text-rose-400 font-bold">-$19.50</span>
        </div>
      </div>
    </Card>
  );
};
