import { useState, useEffect } from 'react';
import { getPerformanceMetrics } from '../services/performanceService';
import { PerformanceMetric } from '../types/performance.types';

export const usePerformance = () => {
  const [metrics, setMetrics] = useState<PerformanceMetric[]>([]);

  useEffect(() => {
    getPerformanceMetrics().then(setMetrics);
  }, []);

  return { metrics };
};
