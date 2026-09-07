import React, { useState } from 'react';
import { Card } from '../../../shared/components/Card';
import { ChartToolbar } from './ChartToolbar';
import { DXChartPanel } from '../../charts/DXChartPanel';

export const MarketChart: React.FC<{ symbol: string }> = ({ symbol }) => {
  const [timeframe, setTimeframe] = useState('M5');

  return (
    <Card title={`${symbol} Interactive Chart`}>
      <ChartToolbar timeframe={timeframe} onTimeframeChange={setTimeframe} />
      <div className="mt-4">
        <DXChartPanel />
      </div>
    </Card>
  );
};
