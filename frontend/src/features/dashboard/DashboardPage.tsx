import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useDashboard } from './hooks/useDashboard';
import { AccountSummary } from './components/AccountSummary';
import { RunningTradesSummary } from './components/RunningTradesSummary';
import { DailyPerformance } from './components/DailyPerformance';
import { WeeklyPerformance } from './components/WeeklyPerformance';
import { PerformanceChart } from './components/PerformanceChart';
import { Spinner } from '../../shared/components/Spinner';

export const DashboardPage: React.FC = () => {
  const { stats, daily, isLoading } = useDashboard();

  if (isLoading || !stats) {
    return (
      <PageContainer title="Dashboard" subtitle="System overview and live trading status">
        <Spinner size="lg" className="py-20" />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Dashboard" subtitle="System overview and live trading status">
      <div className="space-y-6">
        <AccountSummary stats={stats} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <PerformanceChart />
            <RunningTradesSummary />
          </div>
          <div className="space-y-6">
            <DailyPerformance data={daily} />
            <WeeklyPerformance />
          </div>
        </div>
      </div>
    </PageContainer>
  );
};
