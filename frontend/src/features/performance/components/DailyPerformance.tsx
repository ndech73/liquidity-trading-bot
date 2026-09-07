import React from 'react';
import { Card } from '../../../shared/components/Card';

export const DailyPerformance: React.FC = () => {
  return (
    <Card title="Daily PnL Distribution">
      <div className="h-40 flex items-center justify-center bg-slate-950 rounded-lg text-xs text-slate-500">
        [Daily P&L Bar Chart]
      </div>
    </Card>
  );
};
