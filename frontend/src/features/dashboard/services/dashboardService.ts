import { apiClient } from '../../../shared/services/apiClient';
import { DashboardStats, PerformanceDay } from '../types/dashboard.types';

export const getDashboardStats = async (): Promise<DashboardStats> => {
  try {
    const res = await apiClient.get<DashboardStats>('/dashboard/stats');
    return res.data;
  } catch {
    return {
      equity: 10450.75,
      balance: 10000.00,
      unrealizedPnL: 450.75,
      realizedPnLToday: 185.20,
      activeTradesCount: 3,
      winRateToday: 75.0,
      openLots: 0.15,
    };
  }
};

export const getDailyPerformance = async (): Promise<PerformanceDay[]> => {
  try {
    const res = await apiClient.get<PerformanceDay[]>('/dashboard/daily');
    return res.data;
  } catch {
    return [
      { date: 'Mon', pnl: 45.50, tradesCount: 4 },
      { date: 'Tue', pnl: -20.00, tradesCount: 2 },
      { date: 'Wed', pnl: 80.25, tradesCount: 5 },
      { date: 'Thu', pnl: 110.00, tradesCount: 3 },
      { date: 'Fri', pnl: 65.40, tradesCount: 4 },
    ];
  }
};
