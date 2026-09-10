import React from 'react';
import { Card } from '../../../shared/components/Card';
import { AnalysisStatusData } from '../types/analysis.types';
import { EmptyState } from '../../../shared/components/EmptyState';

export const VolatilityPanel: React.FC<{ status: AnalysisStatusData | null }> = ({ status }) => {
  return (
    <Card title="Volatility Regime & Compression">
      {!status?.hasData ? (
        <EmptyState title="No Volatility Data" description="Awaiting market feed or snapshot analysis." />
      ) : (
        <div className="grid grid-cols-2 gap-3 text-center text-xs">
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-400">Compression Ratio</span>
            <p className="text-lg font-mono font-bold text-sky-400 mt-1">
              {status.compressionRatio !== null ? status.compressionRatio.toFixed(2) : 'N/A'}
            </p>
            <span className={`text-xs ${status.isCompressed ? 'text-amber-400' : 'text-slate-400'}`}>
              {status.isCompressed ? 'Compressed' : 'Normal Range'}
            </span>
          </div>
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
            <span className="text-slate-400">Expansion Multiplier</span>
            <p className="text-lg font-mono font-bold text-emerald-400 mt-1">
              {status.expansionRatio !== null ? `${status.expansionRatio.toFixed(2)}x` : 'N/A'}
            </p>
            <span className={`text-xs ${status.isExpanded ? 'text-emerald-400' : 'text-slate-400'}`}>
              {status.isExpanded ? 'Expansion Active' : 'Normal Volatility'}
            </span>
          </div>
        </div>
      )}
    </Card>
  );
};

