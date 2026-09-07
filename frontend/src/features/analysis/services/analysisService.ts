import { LiquidityZone, SweepEvent } from '../types/analysis.types';

export const getLiquidityZones = async (_symbol: string): Promise<LiquidityZone[]> => {
  return [
    { id: 'lz-1', priceHigh: 1.0890, priceLow: 1.0880, type: 'BUY_SIDE', strength: 0.85, isSwept: false },
    { id: 'lz-2', priceHigh: 1.0815, priceLow: 1.0805, type: 'SELL_SIDE', strength: 0.92, isSwept: true },
  ];
};

export const getSweepEvents = async (symbol: string): Promise<SweepEvent[]> => {
  return [
    { id: 'se-1', symbol, timestamp: '2026-09-07 05:45:00', price: 1.0804, sweepType: 'LOW_SWEEP', reactionMagnitudePips: 24.5 },
  ];
};
