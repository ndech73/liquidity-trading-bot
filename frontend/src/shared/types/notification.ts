export interface LiquidityAlert {
  id: string;
  symbol: string;
  timeframe: string;
  direction: 'BUY' | 'SELL';
  entryPrice: number;
  stopLoss: number;
  takeProfit1: number;
  takeProfit2: number;
  riskPips: number;
  rrRatio: number;
  setupType: string;
  reason: string;
  timestamp: string;
  isTest?: boolean;
}

export interface SweepNotice {
  id: string;
  symbol: string;
  timeframe: string;
  side: string;
  liquidityType: string;
  levelPrice: number;
  sweepPrice: number;
  occurredAt: string;
}
