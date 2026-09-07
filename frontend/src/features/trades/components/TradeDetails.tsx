import React from 'react';
import { ActiveTrade } from '../types/trade.types';
import { Card } from '../../../shared/components/Card';
import { formatCurrency } from '../../../shared/utils/formatCurrency';

export const TradeDetails: React.FC<{ trade: ActiveTrade | null }> = ({ trade }) => {
  if (!trade) return null;

  return (
    <Card title={`Ticket #${trade.ticket} Details`}>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
        <div><span className="text-slate-400">Symbol:</span> <p className="font-bold text-slate-100">{trade.symbol}</p></div>
        <div><span className="text-slate-400">Direction:</span> <p className="font-bold text-slate-100">{trade.type}</p></div>
        <div><span className="text-slate-400">P&L:</span> <p className="font-bold text-emerald-400">{formatCurrency(trade.profit)}</p></div>
        <div><span className="text-slate-400">Open Time:</span> <p className="text-slate-300">{trade.openTime}</p></div>
      </div>
    </Card>
  );
};
