import React from 'react';
import { Card } from '../../../shared/components/Card';
import { PerformanceDay } from '../types/performance.types';
import { formatCurrency } from '../../../shared/utils/formatCurrency';
import { EmptyState } from '../../../shared/components/EmptyState';

export const DailyPerformance: React.FC<{ dailyPnl?: PerformanceDay[] }> = ({ dailyPnl = [] }) => {
  return (
    <Card title="Daily PnL Distribution">
      {dailyPnl.length === 0 ? (
        <EmptyState title="No Closed Trades" description="Historical daily performance will populate as positions close." />
      ) : (
        <div className="space-y-2">
          {dailyPnl.map((day) => (
            <div key={day.date} className="flex items-center justify-between py-2 border-b border-slate-800/60 text-xs">
              <span className="text-slate-300 font-mono">{day.date} ({day.tradesCount} trades)</span>
              <span className={`font-mono font-semibold ${day.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {day.pnl >= 0 ? '+' : ''}{formatCurrency(day.pnl)}
              </span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

