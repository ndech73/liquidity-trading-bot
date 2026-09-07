import React from 'react';
import { Card } from '../../../shared/components/Card';

export const WinRate: React.FC = () => {
  return (
    <Card title="Win / Loss Count">
      <div className="flex justify-around items-center py-4">
        <div className="text-center">
          <span className="text-2xl font-bold font-mono text-emerald-400">35</span>
          <p className="text-xs text-slate-400 mt-1">Wins</p>
        </div>
        <div className="text-center">
          <span className="text-2xl font-bold font-mono text-rose-400">14</span>
          <p className="text-xs text-slate-400 mt-1">Losses</p>
        </div>
      </div>
    </Card>
  );
};
