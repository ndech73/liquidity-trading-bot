import React from 'react';
import { Card } from '../../../shared/components/Card';

export const StructurePanel: React.FC = () => {
  return (
    <Card title="Market Structure Analysis">
      <div className="space-y-2 text-xs">
        <div className="flex justify-between py-1 border-b border-slate-800">
          <span className="text-slate-400">Higher Timeframe (H1)</span>
          <span className="font-bold text-emerald-400">BULLISH ORDER FLOW</span>
        </div>
        <div className="flex justify-between py-1 border-b border-slate-800">
          <span className="text-slate-400">Execution Timeframe (M5)</span>
          <span className="font-bold text-sky-400">CHoCH CONFIRMED</span>
        </div>
        <div className="flex justify-between py-1">
          <span className="text-slate-400">Last Structure Break</span>
          <span className="font-mono text-slate-300">1.08480 (12 mins ago)</span>
        </div>
      </div>
    </Card>
  );
};
