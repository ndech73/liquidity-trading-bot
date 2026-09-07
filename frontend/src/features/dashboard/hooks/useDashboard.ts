import { useState, useEffect } from 'react';
import { getDashboardStats, getDailyPerformance } from '../services/dashboardService';
import { DashboardStats, PerformanceDay } from '../types/dashboard.types';

export const useDashboard = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [daily, setDaily] = useState<PerformanceDay[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([getDashboardStats(), getDailyPerformance()]).then(([s, d]) => {
      setStats(s);
      setDaily(d);
      setIsLoading(false);
    });
  }, []);

  return { stats, daily, isLoading };
};
