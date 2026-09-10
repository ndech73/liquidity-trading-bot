import React from 'react';
import { MarketOverview } from '../types/market.types';

export const MarketStatus: React.FC<{ symbol: string; market?: MarketOverview }> = ({ symbol, market }) => {
  const isLive = Boolean(market && market.bid > 0);

  return (
    <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex flex-wrap items-center justify-between gap-3 text-xs">
      <div className="flex items-center gap-4">
        <div>
          <span className="text-slate-400">Selected: </span>
          <span className="font-bold text-slate-100">{symbol}</span>
        </div>
        <div>
          <span className="text-slate-400">Feed: </span>
          <span className={`font-semibold ${isLive ? 'text-emerald-400' : 'text-amber-400'}`}>
            {isLive ? 'LIVE' : 'STANDBY'}
          </span>
        </div>
      </div>
      {market && isLive ? (
        <div className="flex items-center gap-4 font-mono">
          <div>
            <span className="text-slate-400">Bid: </span>
            <span className="text-slate-200 font-semibold">{market.bid.toFixed(5)}</span>
          </div>
          <div>
            <span className="text-slate-400">Ask: </span>
            <span className="text-slate-200 font-semibold">{market.ask.toFixed(5)}</span>
          </div>
          <div>
            <span className="text-slate-400">Spread: </span>
            <span className="text-sky-400">{market.spreadPips} pips</span>
          </div>
        </div>
      ) : (
        <div className="text-slate-500 italic">
          MT5 quotes awaiting live tick reception
        </div>
      )}
    </div>
  );
};

