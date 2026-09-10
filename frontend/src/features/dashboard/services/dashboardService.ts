import { apiClient } from '../../../shared/services/apiClient';
import { DashboardStats, PerformanceDay } from '../types/dashboard.types';

export const getDashboardStats = async (): Promise<DashboardStats> => {
  const res = await apiClient.get<DashboardStats>('/dashboard/stats');
  return res.data;
};

export const getDailyPerformance = async (): Promise<PerformanceDay[]> => {
  const res = await apiClient.get<PerformanceDay[]>('/dashboard/daily');
  return res.data;
};

export interface EquityPoint {
  time: number;
  value: number;
}

export const getEquityCurve = async (): Promise<EquityPoint[]> => {
  const res = await apiClient.get<EquityPoint[]>('/dashboard/equity-curve');
  return res.data;
};
