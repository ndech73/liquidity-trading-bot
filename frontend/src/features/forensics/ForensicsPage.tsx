import React, { useState } from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useTradeForensics } from './hooks/useTradeForensics';
import { TradeTimeline } from './components/TradeTimeline';
import { TradeReasoning } from './components/TradeReasoning';
import { ForensicDetails } from './components/ForensicDetails';
import { Spinner } from '../../shared/components/Spinner';
import { ErrorState } from '../../shared/components/ErrorState';
import { EmptyState } from '../../shared/components/EmptyState';

export const ForensicsPage: React.FC = () => {
  const { records, isLoading, error, refetch } = useTradeForensics();
  const [selectedId, setSelectedId] = useState<string | null>(null);

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
      <div className="space-y-6">
        {records.length > 1 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {records.map((r) => (
              <button
                key={r.tradeId}
                onClick={() => setSelectedId(r.tradeId)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition border ${
                  selectedRecord.tradeId === r.tradeId
                    ? 'bg-sky-500/10 border-sky-500 text-sky-400'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                }`}
              >
                {r.tradeId} ({r.symbol})
              </button>
            ))}
          </div>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <TradeTimeline record={selectedRecord} />
          <TradeReasoning record={selectedRecord} />
          <div className="lg:col-span-2">
            <ForensicDetails record={selectedRecord} />
          </div>
        </div>
      </div>
    </PageContainer>
  );
};

