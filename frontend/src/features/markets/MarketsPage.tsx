import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useMarketData } from './hooks/useMarketData';
import { MarketSelector } from './components/MarketSelector';
import { MarketChart } from './components/MarketChart';
import { MarketStatus } from './components/MarketStatus';

export const MarketsPage: React.FC = () => {
  const { markets, selectedSymbol, setSelectedSymbol } = useMarketData();

  return (
    <PageContainer title="Markets & Charts" subtitle="Multi-asset live price feed and candlestick structures">
      <div className="space-y-4">
        <MarketSelector markets={markets} selected={selectedSymbol} onSelect={setSelectedSymbol} />
        <MarketStatus symbol={selectedSymbol} />
        <MarketChart symbol={selectedSymbol} />
      </div>
    </PageContainer>
  );
};
