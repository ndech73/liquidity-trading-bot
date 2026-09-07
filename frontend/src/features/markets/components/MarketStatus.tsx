import React from 'react';

export const MarketStatus: React.FC<{ symbol: string }> = ({ symbol }) => {
  return (
    <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between text-xs">
      <div>
        <span className="text-slate-400">Status: </span>
        <span className="text-emerald-400 font-semibold">MARKET OPEN</span>
      </div>
      <div>
        <span className="text-slate-400">Selected: </span>
        <span className="font-bold text-slate-200">{symbol}</span>
      </div>
    </div>
  );
};
