import React from 'react';
import { Card } from '../../../shared/components/Card';
import { PerformanceMetric } from '../types/performance.types';

export const PerformanceSummary: React.FC<{ metrics: PerformanceMetric[] }> = ({ metrics }) => {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {metrics.map((m) => (
        <Card key={m.label} title={m.label}>
          <p className={`text-2xl font-mono font-bold ${m.isPositive ? 'text-emerald-400' : 'text-slate-200'}`}>
            {m.value}
          </p>
        </Card>
      ))}
    </div>
  );
};
