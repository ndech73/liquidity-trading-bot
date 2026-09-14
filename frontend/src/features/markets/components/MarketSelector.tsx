import React from 'react';
import { MarketOverview } from '../types/market.types';
import { Activity, ChevronRight } from 'lucide-react';

export const MarketSelector: React.FC<{
  markets: MarketOverview[];
  selected: string;
  onSelect: (sym: string) => void;
}> = ({ markets, selected, onSelect }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col shadow-sm">
      <div className="flex items-center justify-between px-1 pb-3 mb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Market Watchlist
          </span>
        </div>
        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
          {markets.length} Pairs
        </span>
      </div>

      <div className="flex flex-col space-y-1 max-h-[620px] overflow-y-auto pr-0.5">
        {markets.map((m) => {
          const isSelected = selected === m.symbol;
          const isLive = m.bid > 0;

          return (
            <button
              key={m.symbol}
              onClick={() => onSelect(m.symbol)}
              aria-current={isSelected ? 'true' : undefined}
              className={`w-full flex items-center justify-between p-2.5 rounded-lg text-xs transition-all border text-left cursor-pointer group ${
                isSelected
                  ? 'bg-sky-500/10 border-sky-500/60 text-sky-300 shadow-xs shadow-sky-500/10'
                  : 'bg-slate-950/40 border-slate-800/80 text-slate-300 hover:bg-slate-800/50 hover:border-slate-700 hover:text-slate-100'
              }`}
            >
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isLive ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
                    }`}
                  />
                  <span className="font-bold text-sm tracking-tight">{m.symbol}</span>
                </div>
                <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                  Spread: {m.spreadPips > 0 ? `${m.spreadPips} p` : '0.0 p'}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <div className="text-right">
                  <div className="font-mono font-semibold text-slate-200">
                    {isLive ? m.bid.toFixed(5) : '0.00000'}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono">
                    {isLive ? m.ask.toFixed(5) : '0.00000'}
                  </div>
                </div>
                <ChevronRight
                  className={`w-3.5 h-3.5 transition-transform ${
                    isSelected ? 'text-sky-400 translate-x-0.5' : 'text-slate-600 group-hover:text-slate-400'
                  }`}
                />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
