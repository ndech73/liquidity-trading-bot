import React from 'react';
import { Card } from '../../../shared/components/Card';
import { ForensicRecord } from '../types/forensic.types';
import { formatCurrency } from '../../../shared/utils/formatCurrency';

export const ForensicDetails: React.FC<{ record: ForensicRecord }> = ({ record }) => {
  return (
    <Card title={`Forensic Audit: ${record.tradeId} (${record.symbol})`} subtitle="Full execution post-mortem audit">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
        <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
          <span className="text-slate-400">Order / Position</span>
          <p className="font-mono font-bold text-slate-100 mt-1">{record.orderType || 'ORDER'} ({record.lots ?? 0.01} lots)</p>
        </div>
        <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
          <span className="text-slate-400">Execution Price</span>
          <p className="font-mono font-bold text-slate-100 mt-1">{record.openPrice?.toFixed(5) ?? 'N/A'}</p>
        </div>
        <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
          <span className="text-slate-400">Net Realized Return</span>
          <p className={`font-mono font-bold mt-1 ${(record.profit ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {formatCurrency(record.profit ?? 0)} ({record.outcomePips >= 0 ? '+' : ''}{record.outcomePips} pips)
          </p>
        </div>
        <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
          <span className="text-slate-400">Exit Timestamp</span>
          <p className="font-mono text-slate-300 mt-1">{record.exitTimestamp || 'Still Active'}</p>
        </div>
      </div>
      <div className="mt-4 pt-3 border-t border-slate-800 text-xs space-y-1 text-slate-300">
        <p><strong className="text-slate-400">Trigger Rule:</strong> {record.triggerReason}</p>
        <p><strong className="text-slate-400">Target Liquidity Pool:</strong> {record.liquidityPoolSwept}</p>
      </div>
    </Card>
  );
};

