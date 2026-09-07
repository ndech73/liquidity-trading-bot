import { ActiveTrade } from '../types/trade.types';

export const getActiveTrades = async (): Promise<ActiveTrade[]> => {
  return [
    {
      id: 't-1',
      ticket: 9812401,
      symbol: 'EURUSD',
      type: 'BUY',
      lots: 0.10,
      openPrice: 1.08450,
      currentPrice: 1.08510,
      stopLoss: 1.08200,
      takeProfit: 1.09100,
      profit: 60.00,
      openTime: '2026-09-07 05:20:10',
    },
    {
      id: 't-2',
      ticket: 9812405,
      symbol: 'GBPUSD',
      type: 'SELL',
      lots: 0.05,
      openPrice: 1.26900,
      currentPrice: 1.26820,
      stopLoss: 1.27250,
      takeProfit: 1.26100,
      profit: 40.00,
      openTime: '2026-09-07 06:05:44',
    },
  ];
};
