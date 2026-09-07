import React, { useState } from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useAnalysis } from './hooks/useAnalysis';
import { AnalysisStatus } from './components/AnalysisStatus';
import { LiquidityPanel } from './components/LiquidityPanel';
import { SweepPanel } from './components/SweepPanel';
import { VolatilityPanel } from './components/VolatilityPanel';
import { StructurePanel } from './components/StructurePanel';

export const AnalysisPage: React.FC = () => {
  const [symbol] = useState('EURUSD');
  const { zones, sweeps } = useAnalysis(symbol);

  return (
    <PageContainer title="Analysis Engine" subtitle="Live liquidity detection, sweep filters, and volatility conditions">
      <div className="space-y-6">
        <AnalysisStatus symbol={symbol} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LiquidityPanel zones={zones} />
          <SweepPanel sweeps={sweeps} />
          <VolatilityPanel />
          <StructurePanel />
        </div>
      </div>
    </PageContainer>
  );
};
