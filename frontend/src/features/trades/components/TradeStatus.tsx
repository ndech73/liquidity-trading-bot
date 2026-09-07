import React from 'react';

export const TradeStatus: React.FC<{ type: 'BUY' | 'SELL' }> = ({ type }) => {
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${
        type === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-rose-950 text-rose-400 border border-rose-800'
      }`}
    >
      {type}
    </span>
  );
};
