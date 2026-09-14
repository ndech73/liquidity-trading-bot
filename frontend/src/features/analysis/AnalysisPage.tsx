import React, { useState } from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useAnalysis } from './hooks/useAnalysis';
import { AnalysisStatus } from './components/AnalysisStatus';
import { LiquidityPanel } from './components/LiquidityPanel';
import { SweepPanel } from './components/SweepPanel';
import { VolatilityPanel } from './components/VolatilityPanel';
import { StructurePanel } from './components/StructurePanel';
import { Spinner } from '../../shared/components/Spinner';
import { ErrorState } from '../../shared/components/ErrorState';
import { MarketChart } from '../markets/components/MarketChart';
import { ScanSearch, ChevronRight, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { CHOSEN_WATCHLIST, DEFAULT_SYMBOL } from '../../config/markets';

const SYMBOLS: readonly string[] = CHOSEN_WATCHLIST;

export const AnalysisPage: React.FC = () => {
  const [symbol, setSymbol] = useState<string>(DEFAULT_SYMBOL);
  const [showPairsList, setShowPairsList] = useState(false);
  const { zones, sweeps, status, isLoading, error, refetch } = useAnalysis(symbol);

  return (
    <PageContainer title="Analysis Engine" subtitle="Live liquidity detection, sweep filters, and volatility conditions">
      <div className="space-y-4">
        {/* Top Control Bar: Quick Currency Ribbon & Pairs Drawer Toggle */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80">
          <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto py-0.5 pr-2">
            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider shrink-0 mr-1 hidden md:inline">
              Pairs:
            </span>
            {SYMBOLS.map((sym) => {
              const isSelected = symbol === sym;
              return (
                <button
                  key={sym}
                  onClick={() => setSymbol(sym)}
                  className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all border cursor-pointer ${
                    isSelected
                      ? 'bg-sky-500/15 border-sky-500 text-sky-300 font-bold shadow-xs shadow-sky-500/10 ring-1 ring-sky-500/40'
                      : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 hover:border-slate-700'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isSelected ? 'bg-sky-400 animate-pulse' : 'bg-slate-600'
                    }`}
                  />
                  <span className="font-sans font-bold">{sym}</span>
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setShowPairsList((prev) => !prev)}
            className="shrink-0 flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer self-end sm:self-center"
          >
            {showPairsList ? (
              <>
                <PanelLeftClose className="w-3.5 h-3.5 text-sky-400" />
                <span>Hide Pairs List (Full Width)</span>
              </>
            ) : (
              <>
                <PanelLeftOpen className="w-3.5 h-3.5 text-sky-400" />
                <span>Monitored Pairs ({SYMBOLS.length})</span>
              </>
            )}
          </button>
        </div>

        {/* Main Content Layout */}
        <div className="flex flex-col lg:flex-row gap-5 items-start">
          {showPairsList && (
            <div className="w-full lg:w-64 shrink-0 bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col shadow-sm transition-all duration-300">
              <div className="flex items-center justify-between px-1 pb-3 mb-2 border-b border-slate-800/80">
                <div className="flex items-center gap-2">
                  <ScanSearch className="w-4 h-4 text-sky-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    Monitored Pairs
                  </span>
                </div>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                  {SYMBOLS.length}
                </span>
              </div>

              <div className="flex flex-col space-y-1 max-h-[620px] overflow-y-auto pr-0.5">
                {SYMBOLS.map((sym) => {
                  const isSelected = symbol === sym;
                  return (
                    <button
                      key={sym}
                      onClick={() => setSymbol(sym)}
                      aria-current={isSelected ? 'true' : undefined}
                      className={`w-full flex items-center justify-between p-2.5 rounded-lg text-xs font-medium transition-all border text-left cursor-pointer group ${
                        isSelected
                          ? 'bg-sky-500/10 border-sky-500/60 text-sky-300 shadow-xs shadow-sky-500/10'
                          : 'bg-slate-950/40 border-slate-800/80 text-slate-300 hover:bg-slate-800/50 hover:border-slate-700 hover:text-slate-100'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            isSelected ? 'bg-sky-400 animate-pulse' : 'bg-slate-600'
                          }`}
                        />
                        <span className="font-bold tracking-tight text-sm">{sym}</span>
                      </div>
                      <ChevronRight
                        className={`w-3.5 h-3.5 transition-transform ${
                          isSelected ? 'text-sky-400 translate-x-0.5' : 'text-slate-600 group-hover:text-slate-400'
                        }`}
                      />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Interactive Chart + Analysis Metrics & Panels */}
          <div className="flex-1 min-w-0 space-y-6 w-full">
            {/* Live Chart Connected to Analysis Engine */}
            <MarketChart symbol={symbol} title={`${symbol} Live Liquidity Chart`} />

          {isLoading ? (
            <Spinner size="lg" className="py-12" />
          ) : error ? (
            <ErrorState message={error} onRetry={refetch} className="my-6" />
          ) : (
            <>
              <AnalysisStatus symbol={symbol} status={status} />
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <LiquidityPanel zones={zones} />
                <SweepPanel sweeps={sweeps} />
                <VolatilityPanel status={status} />
                <StructurePanel status={status} />
              </div>
            </>
          )}
          </div>
        </div>
      </div>
    </PageContainer>
  );
};
