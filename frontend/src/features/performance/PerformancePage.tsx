import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { usePerformance } from './hooks/usePerformance';
import { PerformanceSummary } from './components/PerformanceSummary';
import { ProfitLossChart } from './components/ProfitLossChart';
import { WinRate } from './components/WinRate';
import { DailyPerformance } from './components/DailyPerformance';

export const PerformancePage: React.FC = () => {
  const { metrics } = usePerformance();

  return (
    <PageContainer title="Performance Analytics" subtitle="Historical trade records and win rate metrics">
      <div className="space-y-6">
        <PerformanceSummary metrics={metrics} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <DailyPerformance />
          </div>
          <div className="space-y-6">
            <ProfitLossChart />
            <WinRate />
          </div>
        </div>
      </div>
    </PageContainer>
  );
};
