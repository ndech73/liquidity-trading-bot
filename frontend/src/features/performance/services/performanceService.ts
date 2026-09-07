import { PerformanceMetric } from '../types/performance.types';

export const getPerformanceMetrics = async (): Promise<PerformanceMetric[]> => {
  return [
    { label: 'Total Net Profit', value: '$2,450.50', isPositive: true },
    { label: 'Profit Factor', value: '2.45', isPositive: true },
    { label: 'Win Rate', value: '71.4%', isPositive: true },
    { label: 'Max Drawdown', value: '4.2%', isPositive: false },
  ];
};
