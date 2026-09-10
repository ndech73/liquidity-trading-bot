import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useTrades } from './hooks/useTrades';
import { ActiveTradesTable } from './components/ActiveTradesTable';
import { Spinner } from '../../shared/components/Spinner';
import { ErrorState } from '../../shared/components/ErrorState';

export const TradesPage: React.FC = () => {
  const { trades, isLoading, error, refetch } = useTrades();

  if (isLoading) {
    return (
      <PageContainer title="Live Orders & Execution" subtitle="Real-time open positions running on MT5 bridge">
        <Spinner size="lg" className="py-20" />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer title="Live Orders & Execution" subtitle="Real-time open positions running on MT5 bridge">
        <ErrorState message={error} onRetry={refetch} className="my-10" />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Live Orders & Execution" subtitle="Real-time open positions running on MT5 bridge">
      <ActiveTradesTable trades={trades} />
    </PageContainer>
  );
};
