import React from 'react';
import { LineChart } from 'lucide-react';
import { Card } from '../../../shared/components/Card';

export const PerformanceChart: React.FC = () => {
  return (
    <Card title="Cumulative Equity Curve" subtitle="Intraday equity progression">
      <div className="h-48 flex items-center justify-center gap-2 bg-slate-950/70 rounded-lg border border-slate-800 text-slate-400 text-sm">
        <LineChart className="w-5 h-5 text-sky-400" />
        <span>Equity Curve Visualization (Intraday Live Feed)</span>
      </div>
    </Card>
  );
};
