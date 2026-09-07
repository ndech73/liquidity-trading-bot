import React from 'react';
import { Card } from '../../../shared/components/Card';

export const WeeklyPerformance: React.FC = () => {
  return (
    <Card title="Weekly Returns (%)">
      <div className="h-40 flex items-center justify-center bg-slate-950 rounded-lg text-xs text-slate-500">
        [Weekly % Returns Chart]
      </div>
    </Card>
  );
};
