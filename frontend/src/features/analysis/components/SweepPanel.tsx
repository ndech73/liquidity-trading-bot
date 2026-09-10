import React from 'react';
import { Card } from '../../../shared/components/Card';
import { SweepEvent } from '../types/analysis.types';
import { EmptyState } from '../../../shared/components/EmptyState';

export const SweepPanel: React.FC<{ sweeps: SweepEvent[] }> = ({ sweeps }) => {
  return (
    <Card title="Recent Sweep Events">
      {sweeps.length === 0 ? (
        <EmptyState title="No Sweep Events" description="No recent liquidity sweep breaches detected." />
      ) : (
        <div className="space-y-2">
          {sweeps.map((s) => (
            <div key={s.id} className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 text-xs flex items-center justify-between">
              <div>
                <span className="font-bold text-rose-400">{s.sweepType}</span>
                <p className="text-slate-400 font-mono mt-0.5">{s.timestamp}</p>
              </div>
              <div className="text-right font-mono">
                <span className="text-slate-200">{s.price.toFixed(5)}</span>
                <span className="block text-emerald-400">+{s.reactionMagnitudePips} pips reaction</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

