import React from 'react';
import { Card } from '../../../shared/components/Card';
import { formatCurrency } from '../../../shared/utils/formatCurrency';

export const ProfitLossChart: React.FC<{ avgWin?: number; avgLoss?: number }> = ({ avgWin = 0, avgLoss = 0 }) => {
  return (
    <Card title="Profit / Loss Ratio">
      <div className="space-y-3 text-xs">
        <div className="flex justify-between">
          <span className="text-slate-400">Average Win:</span>
          <span className="font-mono text-emerald-400 font-bold">
            +{formatCurrency(avgWin)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Average Loss:</span>
          <span className="font-mono text-rose-400 font-bold">
            -{formatCurrency(avgLoss)}
          </span>
        </div>
      </div>
    </Card>
  );
};

