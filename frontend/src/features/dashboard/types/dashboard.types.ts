export interface DashboardStats {
  equity: number;
  balance: number;
  unrealizedPnL: number;
  realizedPnLToday: number;
  activeTradesCount: number;
  winRateToday: number;
  openLots: number;
}

export interface PerformanceDay {
  date: string;
  pnl: number;
  tradesCount: number;
}
