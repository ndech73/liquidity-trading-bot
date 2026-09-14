import React from 'react';
import { Layers, Scan } from 'lucide-react';

export interface ChartToolbarProps {
  timeframe: string;
  onTimeframeChange: (tf: string) => void;
  showLiquidity?: boolean;
  onToggleLiquidity?: () => void;
  showTargets?: boolean;
  onToggleTargets?: () => void;
  onFitContent?: () => void;
}

export const ChartToolbar: React.FC<ChartToolbarProps> = ({
  timeframe,
  onTimeframeChange,
  showLiquidity = true,
  onToggleLiquidity,
  showTargets = true,
  onToggleTargets,
  onFitContent,
}) => {
  const timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 w-full pb-2 border-b border-slate-800">
      <div className="flex items-center gap-1.5 overflow-x-auto py-0.5">
        {timeframes.map((tf) => (
          <button
            key={tf}
            onClick={() => onTimeframeChange(tf)}
            className={`px-2.5 py-1 text-xs font-semibold rounded transition cursor-pointer ${
              timeframe === tf
                ? 'bg-sky-500 text-slate-950 font-bold shadow-xs'
                : 'bg-slate-800/80 text-slate-300 hover:bg-slate-700 hover:text-slate-100'
            }`}
          >
            {tf}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-2">
        {onToggleLiquidity && (
          <button
            onClick={onToggleLiquidity}
            title={showLiquidity ? 'Hide Pinpoint Liquidity Markers' : 'Show Pinpoint Liquidity Markers'}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded border transition cursor-pointer ${
              showLiquidity
                ? 'bg-rose-500/15 border-rose-500/50 text-rose-300 shadow-xs shadow-rose-500/10'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-rose-400" />
            <span>Pinpoint Liquidity</span>
          </button>
        )}

        {onToggleTargets && (
          <button
            onClick={onToggleTargets}
            title={showTargets ? 'Hide Target Level Lines' : 'Show Target Level Lines'}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded border transition cursor-pointer ${
              showTargets
                ? 'bg-emerald-500/15 border-emerald-500/50 text-emerald-300 shadow-xs shadow-emerald-500/10'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            <span className="w-2 h-0.5 bg-emerald-400 rounded-full" />
            <span>Key Targets</span>
          </button>
        )}

        {onFitContent && (
          <button
            onClick={onFitContent}
            title="Auto-fit chart candlesticks to full width"
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-slate-600 transition cursor-pointer"
          >
            <Scan className="w-3.5 h-3.5 text-sky-400" />
            <span>Fit Width</span>
          </button>
        )}
      </div>
    </div>
  );
};
