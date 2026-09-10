export interface PerformanceMetric {
  label: string;
  value: string | number;
  subtext?: string;
  isPositive?: boolean;
}

export interface PerformanceDay {
  date: string;
  pnl: number;
  tradesCount: number;
}

export interface PerformanceResponse {
  metrics: PerformanceMetric[];
  winCount: number;
  lossCount: number;
  avgWin: number;
  avgLoss: number;
  dailyPnl: PerformanceDay[];
  totalTrades: number;
}

