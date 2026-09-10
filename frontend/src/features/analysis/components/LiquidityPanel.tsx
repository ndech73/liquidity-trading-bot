import React from 'react';
import { Card } from '../../../shared/components/Card';
import { LiquidityZone } from '../types/analysis.types';
import { EmptyState } from '../../../shared/components/EmptyState';

export const LiquidityPanel: React.FC<{ zones: LiquidityZone[] }> = ({ zones }) => {
  return (
    <Card title="Detected Liquidity Pools">
      {zones.length === 0 ? (
        <EmptyState title="No Liquidity Zones" description="No liquidity pools identified for this symbol." />
      ) : (
        <div className="space-y-2">
          {zones.map((z) => (
            <div key={z.id} className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center justify-between text-xs">
              <div>
                <span className={`font-bold ${z.type === 'BUY_SIDE' ? 'text-sky-400' : 'text-amber-400'}`}>{z.type}</span>
                <p className="font-mono text-slate-300 mt-0.5">{z.priceLow.toFixed(5)} - {z.priceHigh.toFixed(5)}</p>
              </div>
              <div className="text-right">
                <span className="text-slate-400">Strength: {((z.strength ?? 0) * 100).toFixed(0)}%</span>
                <span className={`block mt-0.5 font-semibold ${z.isSwept ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {z.isSwept ? 'SWEPT' : 'ACTIVE'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

