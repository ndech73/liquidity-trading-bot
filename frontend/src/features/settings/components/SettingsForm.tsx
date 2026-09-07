import React from 'react';
import { BotSettings } from '../types/settings.types';
import { Button } from '../../../shared/components/Button';
import { Card } from '../../../shared/components/Card';

export const SettingsForm: React.FC<{ settings: BotSettings }> = ({ settings }) => {
  return (
    <Card title="Algorithmic Parameters" subtitle="Configure risk rules and MT5 Wine Bridge parameters">
      <form className="space-y-4 max-w-xl text-sm" onSubmit={(e) => e.preventDefault()}>
        <div>
          <label className="block text-slate-300 font-medium mb-1">Max Risk Per Trade (%)</label>
          <input
            type="number"
            defaultValue={settings.maxRiskPerTradePercent}
            step="0.1"
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 font-mono"
          />
        </div>
        <div>
          <label className="block text-slate-300 font-medium mb-1">Compression Ratio Threshold</label>
          <input
            type="number"
            defaultValue={settings.compressionThreshold}
            step="0.05"
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 font-mono"
          />
        </div>
        <div>
          <label className="block text-slate-300 font-medium mb-1">Expansion Ratio Threshold</label>
          <input
            type="number"
            defaultValue={settings.expansionThreshold}
            step="0.05"
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 font-mono"
          />
        </div>
        <div>
          <label className="block text-slate-300 font-medium mb-1">Wine Bridge RPC Port</label>
          <input
            type="number"
            defaultValue={settings.bridgePort}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 font-mono"
          />
        </div>
        <Button type="submit" variant="primary">Save Configuration</Button>
      </form>
    </Card>
  );
};
