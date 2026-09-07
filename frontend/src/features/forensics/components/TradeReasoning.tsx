import React from 'react';
import { Card } from '../../../shared/components/Card';

export const TradeReasoning: React.FC = () => {
  return (
    <Card title="Signal Decision Matrix">
      <div className="space-y-2 text-xs">
        <div className="flex justify-between p-2 bg-slate-950/60 rounded">
          <span className="text-slate-400">Liquidity Sweep Score</span>
          <span className="font-mono text-emerald-400 font-bold">9.2 / 10</span>
        </div>
        <div className="flex justify-between p-2 bg-slate-950/60 rounded">
          <span className="text-slate-400">Volatility Filter</span>
          <span className="font-mono text-emerald-400 font-bold">PASSED (1.62x)</span>
        </div>
        <div className="flex justify-between p-2 bg-slate-950/60 rounded">
          <span className="text-slate-400">Risk-Reward Ratio</span>
          <span className="font-mono text-sky-400 font-bold">1 : 2.8</span>
        </div>
      </div>
    </Card>
  );
};
