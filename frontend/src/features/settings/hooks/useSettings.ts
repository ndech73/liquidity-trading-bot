import { useState, useEffect, useCallback } from 'react';
import { getBotSettings, saveBotSettings as apiSaveSettings } from '../services/settingsService';
import { BotSettings } from '../types/settings.types';

export const useSettings = () => {
  const [settings, setSettings] = useState<BotSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getBotSettings();
      setSettings(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch settings');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const saveSettings = async (newSettings: BotSettings) => {
    setIsSaving(true);
    setError(null);
    try {
      const saved = await apiSaveSettings(newSettings);
      setSettings(saved);
      return true;
    } catch (err: any) {
      setError(err?.message || 'Failed to save settings');
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  return { settings, setSettings, isLoading, isSaving, error, saveSettings, refetch: fetchSettings };
};

