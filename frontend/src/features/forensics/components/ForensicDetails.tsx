import React from 'react';
import { Card } from '../../../shared/components/Card';
import { ForensicRecord } from '../types/forensic.types';

export const ForensicDetails: React.FC<{ record: ForensicRecord }> = ({ record }) => {
  return (
    <Card title={`Forensic Audit: ${record.tradeId}`}>
      <div className="space-y-2 text-xs">
        <p><strong className="text-slate-400">Trigger Rule:</strong> {record.triggerReason}</p>
        <p><strong className="text-slate-400">Target Pool:</strong> {record.liquidityPoolSwept}</p>
        <p><strong className="text-slate-400">Net Return:</strong> <span className="font-mono text-emerald-400 font-bold">+{record.outcomePips} Pips</span></p>
      </div>
    </Card>
  );
};
