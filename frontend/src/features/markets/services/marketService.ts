import { apiClient } from '../../../shared/services/apiClient';
import { MarketOverview } from '../types/market.types';

export const getMarketList = async (): Promise<MarketOverview[]> => {
  const res = await apiClient.get<MarketOverview[]>('/markets');
  return res.data;
};

export const getCandleData = async (symbol: string, timeframe = '5m', count = 100) => {
  const res = await apiClient.get<{ symbol: string; timeframe: string; count: number; candles: any[] }>(
    `/markets/${symbol}/candles`,
    { params: { timeframe, count } }
  );
  return res.data;
};
