import { useState, useEffect, useCallback } from 'react';
import { getPerformanceMetrics } from '../services/performanceService';
import { PerformanceResponse } from '../types/performance.types';

export const usePerformance = () => {
  const [data, setData] = useState<PerformanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPerformance = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getPerformanceMetrics();
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch performance metrics from backend');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPerformance();
  }, [fetchPerformance]);

  return {
    data,
    metrics: data?.metrics || [],
    isLoading,
    error,
    refetch: fetchPerformance,
  };
};

