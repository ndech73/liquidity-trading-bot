import React from 'react';
import { Card } from '../../../shared/components/Card';
import { ForensicRecord } from '../types/forensic.types';
import { EmptyState } from '../../../shared/components/EmptyState';

export const TradeReasoning: React.FC<{ record?: ForensicRecord | null }> = ({ record }) => {
  if (!record) {
    return (
      <Card title="Signal Decision Matrix">
        <EmptyState title="No Decision Matrix" description="Select a trade record to view decision metrics." />
      </Card>
    );
  }

  return (
    <Card title={`Signal Decision Matrix: ${record.tradeId}`}>
      <div className="space-y-2 text-xs">
        <div className="flex justify-between p-2 bg-slate-950/60 rounded">
          <span className="text-slate-400">Target Pool Swept</span>
          <span className="font-mono text-emerald-400 font-bold">{record.liquidityPoolSwept}</span>
        </div>
        <div className="flex justify-between p-2 bg-slate-950/60 rounded">
          <span className="text-slate-400">Volatility Context</span>
          <span className="font-mono text-sky-400 font-bold">
            {record.volatilityAtEntry ? `${record.volatilityAtEntry} ATR` : 'Verified'}
          </span>
        </div>
        <div className="flex justify-between p-2 bg-slate-950/60 rounded">
          <span className="text-slate-400">Risk-Reward Ratio</span>
          <span className="font-mono text-amber-400 font-bold">
            1 : {record.riskRewardRatio ? record.riskRewardRatio.toFixed(1) : '2.0'}
          </span>
        </div>
        <div className="flex justify-between p-2 bg-slate-950/60 rounded">
          <span className="text-slate-400">Strategy Rule</span>
          <span className="font-mono text-slate-200">{record.triggerReason}</span>
        </div>
      </div>
    </Card>
  );
};

