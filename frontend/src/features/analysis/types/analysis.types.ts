export type LiquidityType =
  | 'swing_high'
  | 'swing_low'
  | 'equal_high'
  | 'equal_low'
  | 'session_high'
  | 'session_low'
  | 'previous_high'
  | 'previous_low'
  | 'BUY_SIDE'
  | 'SELL_SIDE';

export type LiquidityStatus = 'active' | 'swept' | 'invalidated';

export interface LiquidityZone {
  id: string;
  symbol?: string;
  timeframe?: string;
  price?: number;
  priceHigh: number;
  priceLow: number;
  type: LiquidityType;
  liquidityType?: LiquidityType;
  status?: LiquidityStatus;
  strength?: number;
  isSwept: boolean;
  createdAt?: string;
  sweptAt?: string;
  sweepPrice?: number;
}

export interface SweepEvent {
  id: string;
  symbol: string;
  timestamp: string;
  price: number;
  sweepType: 'HIGH_SWEEP' | 'LOW_SWEEP';
  reactionMagnitudePips: number;
}

export interface AnalysisStatusData {
  symbol: string;
  hasData: boolean;
  regime: string | null;
  atr: number | null;
  compressionRatio: number | null;
  isCompressed: boolean;
  expansionRatio: number | null;
  isExpanded: boolean;
  higherTimeframeStructure: string | null;
  executionTimeframeStructure: string | null;
  lastStructureBreak: string | null;
}

