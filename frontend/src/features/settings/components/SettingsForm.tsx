import React, { useState, useEffect } from 'react';
import { BotSettings } from '../types/settings.types';
import { Button } from '../../../shared/components/Button';
import { Card } from '../../../shared/components/Card';

export const SettingsForm: React.FC<{
  settings: BotSettings;
  onSave?: (s: BotSettings) => Promise<boolean>;
  isSaving?: boolean;
}> = ({ settings, onSave, isSaving = false }) => {
  const [formData, setFormData] = useState<BotSettings>(settings);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    setFormData(settings);
  }, [settings]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (onSave) {
      const ok = await onSave(formData);
      if (ok) {
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      }
    }
  };

  return (
    <Card title="Algorithmic Parameters" subtitle="Configure risk rules and MT5 Wine Bridge parameters">
      <form className="space-y-4 max-w-xl text-sm" onSubmit={handleSubmit}>
        {saveSuccess && (
          <div className="p-3 bg-emerald-950/60 border border-emerald-800 text-emerald-300 rounded-lg text-xs font-semibold">
            Parameters updated successfully in backend runtime.
          </div>
        )}
        <div>
          <label className="block text-slate-300 font-medium mb-1">Max Risk Per Trade (%)</label>
          <input
            type="number"
            value={formData.maxRiskPerTradePercent}
            onChange={(e) => setFormData({ ...formData, maxRiskPerTradePercent: parseFloat(e.target.value) || 0 })}
            step="0.1"
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 font-mono"
          />
        </div>
        <div>
          <label className="block text-slate-300 font-medium mb-1">Compression Ratio Threshold</label>
          <input
            type="number"
            value={formData.compressionThreshold}
            onChange={(e) => setFormData({ ...formData, compressionThreshold: parseFloat(e.target.value) || 0 })}
            step="0.05"
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 font-mono"
          />
        </div>
        <div>
          <label className="block text-slate-300 font-medium mb-1">Expansion Ratio Threshold</label>
          <input
            type="number"
            value={formData.expansionThreshold}
            onChange={(e) => setFormData({ ...formData, expansionThreshold: parseFloat(e.target.value) || 0 })}
            step="0.05"
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 font-mono"
          />
        </div>
        <div>
          <label className="block text-slate-300 font-medium mb-1">Wine Bridge RPC Port</label>
          <input
            type="number"
            value={formData.bridgePort}
            onChange={(e) => setFormData({ ...formData, bridgePort: parseInt(e.target.value, 10) || 0 })}
            className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-100 font-mono"
          />
        </div>
        <Button type="submit" variant="primary" disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save Configuration'}
        </Button>
      </form>
    </Card>
  );
};

