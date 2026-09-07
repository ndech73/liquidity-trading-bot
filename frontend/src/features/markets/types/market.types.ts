export interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketOverview {
  symbol: string;
  bid: number;
  ask: number;
  spreadPips: number;
  change24h: number;
}
