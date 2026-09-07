import { useState, useEffect } from 'react';
import { getBotSettings } from '../services/settingsService';
import { BotSettings } from '../types/settings.types';

export const useSettings = () => {
  const [settings, setSettings] = useState<BotSettings | null>(null);

  useEffect(() => {
    getBotSettings().then(setSettings);
  }, []);

  return { settings, setSettings };
};
