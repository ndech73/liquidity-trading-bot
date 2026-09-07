import React, { useState } from 'react';
import { ActiveTrade } from '../types/trade.types';
import { TradeRow } from './TradeRow';
import { TradeDetails } from './TradeDetails';
import { EmptyState } from '../../../shared/components/EmptyState';

export const ActiveTradesTable: React.FC<{ trades: ActiveTrade[] }> = ({ trades }) => {
  const [selectedTrade, setSelectedTrade] = useState<ActiveTrade | null>(null);

  if (trades.length === 0) {
    return <EmptyState title="No Active Trades" description="The strategy engine has no open MT5 orders currently." />;
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <th className="p-3">Ticket</th>
              <th className="p-3">Symbol</th>
              <th className="p-3">Type</th>
              <th className="p-3">Lots</th>
              <th className="p-3">Open</th>
              <th className="p-3">Current</th>
              <th className="p-3">SL</th>
              <th className="p-3">TP</th>
              <th className="p-3">Profit</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <TradeRow key={t.id} trade={t} onSelect={setSelectedTrade} />
            ))}
          </tbody>
        </table>
      </div>
      <TradeDetails trade={selectedTrade} />
    </div>
  );
};
