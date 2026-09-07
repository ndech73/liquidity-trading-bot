import { ForensicRecord } from '../types/forensic.types';

export const getForensicRecords = async (): Promise<ForensicRecord[]> => {
  return [
    {
      tradeId: 't-981',
      symbol: 'EURUSD',
      triggerReason: 'Asian Low Sweep + M5 Bullish Engulfing with Expansion > 1.5x',
      liquidityPoolSwept: '1.08050 Low',
      volatilityAtEntry: 1.62,
      entryTimestamp: '2026-09-07 05:20:10',
      outcomePips: 24.5,
    },
  ];
};
