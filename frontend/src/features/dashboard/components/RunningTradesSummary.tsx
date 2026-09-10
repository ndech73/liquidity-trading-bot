import React from 'react';
import { Card } from '../../../shared/components/Card';
import { EmptyState } from '../../../shared/components/EmptyState';
import { ActiveTrade } from '../../trades/types/trade.types';

export const RunningTradesSummary: React.FC<{ trades?: ActiveTrade[] }> = ({ trades = [] }) => {
  return (
    <Card title="Running Orders Summary" subtitle="Live positions synced with MetaTrader 5">
      {trades.length === 0 ? (
        <EmptyState
          title="No Open Positions"
          description="The MetaTrader 5 execution engine currently has zero open orders."
          className="py-8"
        />
      ) : (
        <div className="space-y-3">
          {trades.map((t) => (
            <div
              key={t.id || t.ticket}
              className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80"
            >
              <div>
                <span className="font-bold text-sm text-slate-200">{t.symbol}</span>
                <span
                  className={`ml-2 px-1.5 py-0.5 text-xs rounded font-mono ${
                    t.type === 'BUY'
                      ? 'bg-emerald-950 text-emerald-400'
                      : 'bg-rose-950 text-rose-400'
                  }`}
                >
                  {t.type} {t.lots}
                </span>
              </div>
              <div className="text-right">
                <span
                  className={`text-sm font-mono font-semibold ${
                    t.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {t.profit >= 0 ? `+$${t.profit.toFixed(2)}` : `-$${Math.abs(t.profit).toFixed(2)}`}
                </span>
                <span className="block text-xs text-slate-400">
                  SL: {t.stopLoss?.toFixed(4) || 'None'} • TP: {t.takeProfit?.toFixed(4) || 'None'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};
