import React, { useState } from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useMarketData } from './hooks/useMarketData';
import { MarketSelector } from './components/MarketSelector';
import { MarketChart } from './components/MarketChart';
import { MarketStatus } from './components/MarketStatus';
import { Spinner } from '../../shared/components/Spinner';
import { ErrorState } from '../../shared/components/ErrorState';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';

export const MarketsPage: React.FC = () => {
  const { markets, selectedSymbol, setSelectedSymbol, isLoading, error, refetch } = useMarketData();
  const [showWatchlist, setShowWatchlist] = useState(false);

  if (isLoading) {
    return (
      <PageContainer title="Markets & Charts" subtitle="Multi-asset live price feed and candlestick structures">
        <Spinner size="lg" className="py-20" />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer title="Markets & Charts" subtitle="Multi-asset live price feed and candlestick structures">
        <ErrorState message={error} onRetry={refetch} className="my-10" />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Markets & Charts" subtitle="Multi-asset live price feed and candlestick structures">
      <div className="space-y-4">
        {/* Top Control Bar: Quick Currency Ticker Ribbon & Watchlist Drawer Toggle */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80">
          {/* Quick-Switch Horizontal Currency Ribbon */}
          <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto py-0.5 pr-2">
            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider shrink-0 mr-1 hidden md:inline">
              Pairs:
            </span>
            {markets.map((m) => {
              const isSelected = m.symbol === selectedSymbol;
              const isLive = m.bid > 0;
              return (
                <button
                  key={m.symbol}
                  onClick={() => setSelectedSymbol(m.symbol)}
                  className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all border cursor-pointer ${
                    isSelected
                      ? 'bg-sky-500/15 border-sky-500 text-sky-300 font-bold shadow-xs shadow-sky-500/10 ring-1 ring-sky-500/40'
                      : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 hover:border-slate-700'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isLive ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
                    }`}
                  />
                  <span className="font-sans font-bold">{m.symbol}</span>
                  {isLive && (
                    <span className="text-slate-400 text-[10px] hidden lg:inline">
                      {m.bid.toFixed(5)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Toggle Full Watchlist Sidebar */}
          <button
            onClick={() => setShowWatchlist((prev) => !prev)}
            className="shrink-0 flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer self-end sm:self-center"
          >
            {showWatchlist ? (
              <>
                <PanelLeftClose className="w-3.5 h-3.5 text-sky-400" />
                <span>Hide Watchlist (Full Width)</span>
              </>
            ) : (
              <>
                <PanelLeftOpen className="w-3.5 h-3.5 text-sky-400" />
                <span>Detailed Watchlist ({markets.length})</span>
              </>
            )}
          </button>
        </div>

        {/* Main Content Layout — Full width when watchlist is hidden, or side-by-side when open */}
        <div className="flex flex-col lg:flex-row gap-5 items-start">
          {showWatchlist && (
            <div className="w-full lg:w-64 shrink-0 transition-all duration-300">
              <MarketSelector markets={markets} selected={selectedSymbol} onSelect={setSelectedSymbol} />
            </div>
          )}

          <div className="flex-1 min-w-0 space-y-4 w-full">
            <MarketStatus
              symbol={selectedSymbol}
              market={markets.find((m) => m.symbol === selectedSymbol)}
            />
            <MarketChart symbol={selectedSymbol} />
          </div>
        </div>
      </div>
    </PageContainer>
  );
};
