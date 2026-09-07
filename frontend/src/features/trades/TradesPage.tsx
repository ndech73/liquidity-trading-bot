import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useTrades } from './hooks/useTrades';
import { ActiveTradesTable } from './components/ActiveTradesTable';
import { Spinner } from '../../shared/components/Spinner';

export const TradesPage: React.FC = () => {
  const { trades, isLoading } = useTrades();

  return (
    <PageContainer title="Live Orders & Execution" subtitle="Real-time open positions running on MT5 bridge">
      {isLoading ? <Spinner size="lg" className="py-20" /> : <ActiveTradesTable trades={trades} />}
    </PageContainer>
  );
};
