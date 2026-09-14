import React, { useState } from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useTradeForensics } from './hooks/useTradeForensics';
import { TradeTimeline } from './components/TradeTimeline';
import { TradeReasoning } from './components/TradeReasoning';
import { ForensicDetails } from './components/ForensicDetails';
import { Spinner } from '../../shared/components/Spinner';
import { ErrorState } from '../../shared/components/ErrorState';
import { EmptyState } from '../../shared/components/EmptyState';
import { MarketChart } from '../markets/components/MarketChart';
import { Fingerprint, ChevronRight, PanelLeftClose, PanelLeftOpen } from 'lucide-react';

export const ForensicsPage: React.FC = () => {
  const { records, isLoading, error, refetch } = useTradeForensics();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showAuditList, setShowAuditList] = useState(false);

  if (isLoading) {
    return (
      <PageContainer title="Trade Forensics" subtitle="Post-trade audit and algorithmic decision logs">
        <Spinner size="lg" className="py-20" />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer title="Trade Forensics" subtitle="Post-trade audit and algorithmic decision logs">
        <ErrorState message={error} onRetry={refetch} className="my-10" />
      </PageContainer>
    );
  }

  if (records.length === 0) {
    return (
      <PageContainer title="Trade Forensics" subtitle="Post-trade audit and algorithmic decision logs">
        <EmptyState
          title="No Forensic Records"
          description="Algorithmic forensic audit logs will appear here once trades are executed and recorded in the database."
          className="my-10"
        />
      </PageContainer>
    );
  }

  const selectedRecord = records.find((r) => r.tradeId === selectedId) || records[0];

  return (
    <PageContainer title="Trade Forensics" subtitle="Post-trade audit and algorithmic decision logs">
      <div className="space-y-4">
        {/* Top Control Bar: Active Case Info & Drawer Toggle */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80">
          <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto py-0.5">
            <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider shrink-0 mr-1 hidden md:inline">
              Audited Trades:
            </span>
            <div className="flex items-center gap-2 overflow-x-auto">
              {records.slice(0, 8).map((r) => {
                const isSelected = selectedRecord.tradeId === r.tradeId;
                return (
                  <button
                    key={r.tradeId}
                    onClick={() => setSelectedId(r.tradeId)}
                    className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all border cursor-pointer ${
                      isSelected
                        ? 'bg-sky-500/15 border-sky-500 text-sky-300 font-bold shadow-xs shadow-sky-500/10 ring-1 ring-sky-500/40'
                        : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/60 hover:text-slate-100 hover:border-slate-700'
                    }`}
                  >
                    <span className="font-sans font-bold">{r.symbol}</span>
                    <span className={`text-[10px] ${r.orderType === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {r.orderType}
                    </span>
                    <span className="text-slate-500 text-[10px]">#{r.ticket || r.tradeId.replace('t-', '')}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <button
            onClick={() => setShowAuditList((prev) => !prev)}
            className="shrink-0 flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer self-end sm:self-center"
          >
            {showAuditList ? (
              <>
                <PanelLeftClose className="w-3.5 h-3.5 text-sky-400" />
                <span>Hide Case Files (Full Width)</span>
              </>
            ) : (
              <>
                <PanelLeftOpen className="w-3.5 h-3.5 text-sky-400" />
                <span>All Case Files ({records.length})</span>
              </>
            )}
          </button>
        </div>

        {/* Main Content Layout */}
        <div className="flex flex-col lg:flex-row gap-5 items-start">
          {showAuditList && (
            <div className="w-full lg:w-72 shrink-0 bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-col shadow-sm transition-all duration-300">
              <div className="flex items-center justify-between px-1 pb-3 mb-2 border-b border-slate-800/80">
                <div className="flex items-center gap-2">
                  <Fingerprint className="w-4 h-4 text-sky-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    Audited Trades
                  </span>
                </div>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                  {records.length} Logs
                </span>
              </div>

              <div className="flex flex-col space-y-1.5 max-h-[640px] overflow-y-auto pr-0.5">
                {records.map((r) => {
                  const isSelected = selectedRecord.tradeId === r.tradeId;
                  const isProfit = (r.profit ?? 0) >= 0;

                  return (
                    <button
                      key={r.tradeId}
                      onClick={() => setSelectedId(r.tradeId)}
                      aria-current={isSelected ? 'true' : undefined}
                      className={`w-full flex items-center justify-between p-2.5 rounded-lg text-xs transition-all border text-left cursor-pointer group ${
                        isSelected
                          ? 'bg-sky-500/10 border-sky-500/60 text-sky-300 shadow-xs shadow-sky-500/10'
                          : 'bg-slate-950/40 border-slate-800/80 text-slate-300 hover:bg-slate-800/50 hover:border-slate-700 hover:text-slate-100'
                      }`}
                    >
                      <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                          <span className="font-bold tracking-tight text-sm text-slate-100">
                            {r.symbol}
                          </span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                              r.orderType === 'BUY'
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                            }`}
                          >
                            {r.orderType}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                          {r.tradeId} • {r.lots} lots
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <div className="text-right font-mono">
                          <div
                            className={`font-semibold ${
                              isProfit ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {isProfit ? '+' : ''}
                            {(r.profit ?? 0).toFixed(2)}
                          </div>
                          <div className="text-[10px] text-slate-500">
                            {r.outcomePips >= 0 ? `+${r.outcomePips}` : r.outcomePips} pips
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
          )}

          {/* Right Column: Case File Details & Forensic Audit */}
          <div className="flex-1 min-w-0 space-y-6 w-full">
            {/* Trade Execution Visual Overlay Chart */}
            <MarketChart
              symbol={selectedRecord.symbol}
              title={`${selectedRecord.symbol} Execution Chart • Trade ${selectedRecord.tradeId}`}
              tradeOverlay={{
                openPrice: selectedRecord.openPrice,
                closePrice: selectedRecord.closePrice,
                stopLoss: selectedRecord.stopLoss,
                takeProfit: selectedRecord.takeProfit,
                orderType: selectedRecord.orderType,
                ticket: selectedRecord.ticket,
                entryTimestamp: selectedRecord.entryTimestamp,
                exitTimestamp: selectedRecord.exitTimestamp,
              }}
            />

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <TradeTimeline record={selectedRecord} />
            <TradeReasoning record={selectedRecord} />
            <div className="xl:col-span-2">
              <ForensicDetails record={selectedRecord} />
            </div>
          </div>
        </div>
      </div>
    </div>
  </PageContainer>
);
};

