import React from 'react';

export const ChartToolbar: React.FC<{
  timeframe: string;
  onTimeframeChange: (tf: string) => void;
}> = ({ timeframe, onTimeframeChange }) => {
  const timeframes = ['M1', 'M5', 'M15', 'H1', 'H4', 'D1'];

  return (
    <div className="flex items-center justify-between pb-3 border-b border-slate-800">
      <div className="flex gap-1.5">
        {timeframes.map((tf) => (
          <button
            key={tf}
            onClick={() => onTimeframeChange(tf)}
            className={`px-2.5 py-1 text-xs font-semibold rounded ${
              timeframe === tf ? 'bg-sky-500 text-slate-950' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {tf}
          </button>
        ))}
      </div>
      <span className="text-xs text-slate-400">Indicators: Liquidity Zones, Volume Profile</span>
    </div>
  );
};
