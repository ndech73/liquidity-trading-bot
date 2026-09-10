import { useState, useEffect, useCallback } from 'react';
import { getDashboardStats, getDailyPerformance } from '../services/dashboardService';
import { getActiveTrades } from '../../trades/services/tradeService';
import { DashboardStats, PerformanceDay } from '../types/dashboard.types';
import { ActiveTrade } from '../../trades/types/trade.types';

export const useDashboard = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [daily, setDaily] = useState<PerformanceDay[]>([]);
  const [trades, setTrades] = useState<ActiveTrade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [s, d, t] = await Promise.all([
        getDashboardStats(),
        getDailyPerformance(),
        getActiveTrades(),
      ]);
      setStats(s);
      setDaily(d);
      setTrades(t);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch dashboard data from backend');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { stats, daily, trades, isLoading, error, refetch: fetchData };
};
