import { apiClient } from '../../../shared/services/apiClient';
import { PerformanceResponse } from '../types/performance.types';

export const getPerformanceMetrics = async (): Promise<PerformanceResponse> => {
  const res = await apiClient.get<PerformanceResponse>('/performance');
  return res.data;
};

