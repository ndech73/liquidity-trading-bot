import React from 'react';
import { Card } from '../../../shared/components/Card';

export const TradeTimeline: React.FC = () => {
  return (
    <Card title="Execution Lifecycle Timeline">
      <ol className="relative border-l border-slate-800 ml-3 space-y-4 text-xs">
        <li className="ml-4">
          <div className="absolute -left-1.5 w-3 h-3 bg-sky-500 rounded-full" />
          <span className="text-slate-400">05:15:00</span>
          <h4 className="font-semibold text-slate-200">Compression Detected (Ratio 0.64)</h4>
        </li>
        <li className="ml-4">
          <div className="absolute -left-1.5 w-3 h-3 bg-amber-500 rounded-full" />
          <span className="text-slate-400">05:18:22</span>
          <h4 className="font-semibold text-slate-200">Sell-Side Liquidity Swept at 1.08050</h4>
        </li>
        <li className="ml-4">
          <div className="absolute -left-1.5 w-3 h-3 bg-emerald-500 rounded-full" />
          <span className="text-slate-400">05:20:10</span>
          <h4 className="font-semibold text-slate-200">BUY Order Dispatched to MT5 Terminal</h4>
        </li>
      </ol>
    </Card>
  );
};
