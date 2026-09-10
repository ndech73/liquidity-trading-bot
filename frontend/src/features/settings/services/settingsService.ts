import { apiClient } from '../../../shared/services/apiClient';
import { BotSettings } from '../types/settings.types';

export const getBotSettings = async (): Promise<BotSettings> => {
  const res = await apiClient.get<BotSettings>('/settings');
  return res.data;
};

export const saveBotSettings = async (settings: BotSettings): Promise<BotSettings> => {
  const res = await apiClient.post<{ status: string; settings: BotSettings }>('/settings', settings);
  return res.data.settings;
};
