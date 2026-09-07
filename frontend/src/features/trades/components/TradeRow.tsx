import React from 'react';
import { ActiveTrade } from '../types/trade.types';
import { TradeStatus } from './TradeStatus';
import { formatCurrency } from '../../../shared/utils/formatCurrency';

export const TradeRow: React.FC<{ trade: ActiveTrade; onSelect?: (t: ActiveTrade) => void }> = ({ trade, onSelect }) => {
  return (
    <tr
      onClick={() => onSelect?.(trade)}
      className="border-b border-slate-800/80 hover:bg-slate-800/50 cursor-pointer text-xs sm:text-sm"
    >
      <td className="p-3 font-mono text-slate-400">#{trade.ticket}</td>
      <td className="p-3 font-bold text-slate-200">{trade.symbol}</td>
      <td className="p-3"><TradeStatus type={trade.type} /></td>
      <td className="p-3 font-mono">{trade.lots.toFixed(2)}</td>
      <td className="p-3 font-mono">{trade.openPrice.toFixed(5)}</td>
      <td className="p-3 font-mono">{trade.currentPrice.toFixed(5)}</td>
      <td className="p-3 font-mono text-slate-400">{trade.stopLoss.toFixed(5)}</td>
      <td className="p-3 font-mono text-slate-400">{trade.takeProfit.toFixed(5)}</td>
      <td className={`p-3 font-mono font-bold ${trade.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
        {formatCurrency(trade.profit)}
      </td>
    </tr>
  );
};
