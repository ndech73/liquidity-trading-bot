export interface TimelineEvent {
  time: string;
  title: string;
  type: 'sweep' | 'order' | 'close';
}

export interface ForensicRecord {
  tradeId: string;
  ticket?: number;
  symbol: string;
  triggerReason: string;
  liquidityPoolSwept: string;
  volatilityAtEntry: number;
  entryTimestamp: string;
  exitTimestamp?: string | null;
  outcomePips: number;
  lots?: number;
  openPrice?: number;
  closePrice?: number | null;
  stopLoss?: number | null;
  takeProfit?: number | null;
  profit?: number;
  orderType?: string;
  riskRewardRatio?: number;
  timeline?: TimelineEvent[];
}

