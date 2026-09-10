import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { usePerformance } from './hooks/usePerformance';
import { PerformanceSummary } from './components/PerformanceSummary';
import { ProfitLossChart } from './components/ProfitLossChart';
import { WinRate } from './components/WinRate';
import { DailyPerformance } from './components/DailyPerformance';
import { Spinner } from '../../shared/components/Spinner';
import { ErrorState } from '../../shared/components/ErrorState';

export const PerformancePage: React.FC = () => {
  const { data, metrics, isLoading, error, refetch } = usePerformance();

  if (isLoading) {
    return (
      <PageContainer title="Performance Analytics" subtitle="Historical trade records and win rate metrics">
        <Spinner size="lg" className="py-20" />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer title="Performance Analytics" subtitle="Historical trade records and win rate metrics">
        <ErrorState message={error} onRetry={refetch} className="my-10" />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Performance Analytics" subtitle="Historical trade records and win rate metrics">
      <div className="space-y-6">
        <PerformanceSummary metrics={metrics} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <DailyPerformance dailyPnl={data?.dailyPnl} />
          </div>
          <div className="space-y-6">
            <ProfitLossChart avgWin={data?.avgWin} avgLoss={data?.avgLoss} />
            <WinRate winCount={data?.winCount} lossCount={data?.lossCount} />
          </div>
        </div>
      </div>
    </PageContainer>
  );
};

