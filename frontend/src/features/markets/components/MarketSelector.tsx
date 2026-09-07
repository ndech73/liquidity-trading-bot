import React from 'react';
import { MarketOverview } from '../types/market.types';

export const MarketSelector: React.FC<{
  markets: MarketOverview[];
  selected: string;
  onSelect: (sym: string) => void;
}> = ({ markets, selected, onSelect }) => {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2">
      {markets.map((m) => (
        <button
          key={m.symbol}
          onClick={() => onSelect(m.symbol)}
          className={`px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition border ${
            selected === m.symbol
              ? 'bg-sky-500/10 border-sky-500 text-sky-400'
              : 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700'
          }`}
        >
          {m.symbol} <span className="font-mono text-slate-400">({m.bid.toFixed(4)})</span>
        </button>
      ))}
    </div>
  );
};
