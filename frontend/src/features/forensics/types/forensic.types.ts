export interface ForensicRecord {
  tradeId: string;
  symbol: string;
  triggerReason: string;
  liquidityPoolSwept: string;
  volatilityAtEntry: number;
  entryTimestamp: string;
  exitTimestamp?: string;
  outcomePips: number;
}
