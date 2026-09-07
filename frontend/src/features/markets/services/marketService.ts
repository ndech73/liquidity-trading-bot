import { MarketOverview } from '../types/market.types';

export const getMarketList = async (): Promise<MarketOverview[]> => {
  return [
    { symbol: 'EURUSD', bid: 1.08502, ask: 1.08512, spreadPips: 1.0, change24h: 0.15 },
    { symbol: 'GBPUSD', bid: 1.26804, ask: 1.26819, spreadPips: 1.5, change24h: -0.22 },
    { symbol: 'USDJPY', bid: 154.210, ask: 154.225, spreadPips: 1.5, change24h: 0.45 },
    { symbol: 'AUDUSD', bid: 0.65401, ask: 0.65413, spreadPips: 1.2, change24h: 0.08 },
  ];
};
