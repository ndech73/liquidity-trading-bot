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

const SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD', 'EURJPY', 'GBPJPY', 'EURGBP'];

export const AnalysisPage: React.FC = () => {
  const [symbol, setSymbol] = useState('EURUSD');
  const { zones, sweeps, status, isLoading, error, refetch } = useAnalysis(symbol);

  return (
    <PageContainer title="Analysis Engine" subtitle="Live liquidity detection, sweep filters, and volatility conditions">
      <div className="space-y-6">
        <div className="flex gap-2 overflow-x-auto pb-1">
          {SYMBOLS.map((sym) => (
            <button
              key={sym}
              onClick={() => setSymbol(sym)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition border ${
                symbol === sym
                  ? 'bg-sky-500/10 border-sky-500 text-sky-400'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              {sym}
            </button>
          ))}
        </div>

        {isLoading ? (
          <Spinner size="lg" className="py-20" />
        ) : error ? (
          <ErrorState message={error} onRetry={refetch} className="my-10" />
        ) : (
          <>
            <AnalysisStatus symbol={symbol} status={status} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <LiquidityPanel zones={zones} />
              <SweepPanel sweeps={sweeps} />
              <VolatilityPanel status={status} />
              <StructurePanel status={status} />
            </div>
          </>
        )}
      </div>
    </PageContainer>
  );
};

