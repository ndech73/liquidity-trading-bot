import React from 'react';
import { Card } from '../../../shared/components/Card';
import { ForensicRecord } from '../types/forensic.types';
import { EmptyState } from '../../../shared/components/EmptyState';

export const TradeTimeline: React.FC<{ record?: ForensicRecord | null }> = ({ record }) => {
  if (!record) {
    return (
      <Card title="Execution Lifecycle Timeline">
        <EmptyState title="No Timeline Data" description="Select a trade record to view its execution lifecycle." />
      </Card>
    );
  }

  const events = record.timeline && record.timeline.length > 0 ? record.timeline : [
    {
      time: record.entryTimestamp,
      title: `${record.triggerReason} (${record.symbol})`,
      type: 'sweep' as const,
    },
    {
      time: record.entryTimestamp,
      title: `Order dispatched to MT5 at ${record.openPrice ?? 'market'}`,
      type: 'order' as const,
    },
    ...(record.exitTimestamp ? [{
      time: record.exitTimestamp,
      title: `Position closed: ${record.outcomePips >= 0 ? '+' : ''}${record.outcomePips} pips`,
      type: 'close' as const,
    }] : []),
  ];

  return (
    <Card title={`Execution Lifecycle Timeline: ${record.tradeId}`}>
      <ol className="relative border-l border-slate-800 ml-3 space-y-4 text-xs">
        {events.map((evt, idx) => (
          <li key={idx} className="ml-4">
            <div className={`absolute -left-1.5 w-3 h-3 rounded-full ${
              evt.type === 'sweep' ? 'bg-amber-500' : evt.type === 'order' ? 'bg-sky-500' : 'bg-emerald-500'
            }`} />
            <span className="text-slate-400 font-mono">{evt.time}</span>
            <h4 className="font-semibold text-slate-200 mt-0.5">{evt.title}</h4>
          </li>
        ))}
      </ol>
    </Card>
  );
};

