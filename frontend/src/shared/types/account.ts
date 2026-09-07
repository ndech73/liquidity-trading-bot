export interface AccountSummaryData {
  login: number;
  server: string;
  currency: string;
  balance: number;
  equity: number;
  margin: number;
  freeMargin: number;
  marginLevel: number;
  openPositionsCount: number;
  dailyPnL: number;
  dailyPnLPercentage: number;
}
