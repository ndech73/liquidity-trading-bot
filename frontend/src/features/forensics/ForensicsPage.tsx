import React from 'react';
import { PageContainer } from '../../layout/PageContainer';
import { useTradeForensics } from './hooks/useTradeForensics';
import { TradeTimeline } from './components/TradeTimeline';
import { TradeReasoning } from './components/TradeReasoning';
import { ForensicDetails } from './components/ForensicDetails';

export const ForensicsPage: React.FC = () => {
  const { records } = useTradeForensics();

  return (
    <PageContainer title="Trade Forensics" subtitle="Post-trade audit and algorithmic decision logs">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TradeTimeline />
        <TradeReasoning />
        {records[0] && <div className="lg:col-span-2"><ForensicDetails record={records[0]} /></div>}
      </div>
    </PageContainer>
  );
};
