import { PerformanceDay } from '../types/dashboard.types';

export const calculateTotalPnL = (days: PerformanceDay[]): number => {
  return days.reduce((acc, curr) => acc + curr.pnl, 0);
};

export const calculateWinRate = (winningTrades: number, totalTrades: number): number => {
  if (totalTrades === 0) return 0;
  return (winningTrades / totalTrades) * 100;
};
