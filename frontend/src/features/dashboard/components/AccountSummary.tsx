import React from 'react';
import { Card } from '../../../shared/components/Card';
import { DashboardStats } from '../types/dashboard.types';
import { formatCurrency } from '../../../shared/utils/formatCurrency';

export const AccountSummary: React.FC<{ stats: DashboardStats }> = ({ stats }) => {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Card title="Account Equity">
        <p className="text-2xl font-bold font-mono text-emerald-400">{formatCurrency(stats.equity)}</p>
        <span className="text-xs text-slate-400 mt-1 block">Balance: {formatCurrency(stats.balance)}</span>
      </Card>
      <Card title="Unrealized P&L">
        <p className={`text-2xl font-bold font-mono ${stats.unrealizedPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
          {formatCurrency(stats.unrealizedPnL)}
        </p>
        <span className="text-xs text-slate-400 mt-1 block">{stats.activeTradesCount} open positions</span>
      </Card>
      <Card title="Daily Realized P&L">
        <p className={`text-2xl font-bold font-mono ${stats.realizedPnLToday >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
          {formatCurrency(stats.realizedPnLToday)}
        </p>
        <span className="text-xs text-slate-400 mt-1 block">Win rate: {stats.winRateToday}%</span>
      </Card>
      <Card title="Market Exposure">
        <p className="text-2xl font-bold font-mono text-sky-400">{stats.openLots} Lots</p>
        <span className="text-xs text-slate-400 mt-1 block">Execution: MT5 Bridge</span>
      </Card>
    </div>
  );
};
