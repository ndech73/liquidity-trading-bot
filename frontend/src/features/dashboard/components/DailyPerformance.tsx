import React from 'react';
import { Card } from '../../../shared/components/Card';
import { PerformanceDay } from '../types/dashboard.types';
import { formatCurrency } from '../../../shared/utils/formatCurrency';

export const DailyPerformance: React.FC<{ data: PerformanceDay[] }> = ({ data }) => {
  return (
    <Card title="Weekly Daily P&L Breakdown">
      <div className="space-y-2">
        {data.map((day) => (
          <div key={day.date} className="flex items-center justify-between py-1.5 border-b border-slate-800/60 text-sm">
            <span className="text-slate-300">{day.date} ({day.tradesCount} trades)</span>
            <span className={`font-mono font-semibold ${day.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {formatCurrency(day.pnl)}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
};
