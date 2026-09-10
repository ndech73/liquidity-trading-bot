import React from 'react';
import { Card } from '../../../shared/components/Card';
import { AnalysisStatusData } from '../types/analysis.types';
import { EmptyState } from '../../../shared/components/EmptyState';

export const StructurePanel: React.FC<{ status: AnalysisStatusData | null }> = ({ status }) => {
  return (
    <Card title="Market Structure Analysis">
      {!status?.hasData ? (
        <EmptyState title="No Structure Data" description="Market structure requires active candlestick feeds." />
      ) : (
        <div className="space-y-2 text-xs">
          <div className="flex justify-between py-1 border-b border-slate-800">
            <span className="text-slate-400">Higher Timeframe (H1)</span>
            <span className={`font-bold ${status.higherTimeframeStructure === 'BULLISH' ? 'text-emerald-400' : 'text-amber-400'}`}>
              {status.higherTimeframeStructure || 'NEUTRAL'}
            </span>
          </div>
          <div className="flex justify-between py-1 border-b border-slate-800">
            <span className="text-slate-400">Execution Timeframe (M5)</span>
            <span className="font-bold text-sky-400">
              {status.executionTimeframeStructure || 'CONSOLIDATING'}
            </span>
          </div>
          <div className="flex justify-between py-1">
            <span className="text-slate-400">Last Structure Candle/Break</span>
            <span className="font-mono text-slate-300">
              {status.lastStructureBreak || 'Awaiting update'}
            </span>
          </div>
        </div>
      )}
    </Card>
  );
};

