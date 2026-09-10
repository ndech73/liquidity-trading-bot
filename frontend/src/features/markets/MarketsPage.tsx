import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useMarketData } from './hooks/useMarketData';
import { MarketSelector } from './components/MarketSelector';
import { MarketChart } from './components/MarketChart';
import { MarketStatus } from './components/MarketStatus';

import { Spinner } from '../../shared/components/Spinner';
import { ErrorState } from '../../shared/components/ErrorState';

export const MarketsPage: React.FC = () => {
  const { markets, selectedSymbol, setSelectedSymbol, isLoading, error, refetch } = useMarketData();

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
        <MarketSelector markets={markets} selected={selectedSymbol} onSelect={setSelectedSymbol} />
        <MarketStatus symbol={selectedSymbol} market={markets.find((m) => m.symbol === selectedSymbol)} />
        <MarketChart symbol={selectedSymbol} />
      </div>
    </PageContainer>
  );
};
