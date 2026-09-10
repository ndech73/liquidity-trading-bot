import { apiClient } from '../../../shared/services/apiClient';
import { ActiveTrade } from '../types/trade.types';

export const getActiveTrades = async (): Promise<ActiveTrade[]> => {
  const res = await apiClient.get<ActiveTrade[]>('/trades');
  return res.data;
};

export const getTradeHistory = async (): Promise<any[]> => {
  const res = await apiClient.get<any[]>('/trades/history');
  return res.data;
};
