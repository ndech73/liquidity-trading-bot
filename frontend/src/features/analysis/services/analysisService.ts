import { apiClient } from '../../../shared/services/apiClient';
import { LiquidityZone, SweepEvent, AnalysisStatusData } from '../types/analysis.types';

export const getLiquidityZones = async (symbol: string): Promise<LiquidityZone[]> => {
  const res = await apiClient.get<LiquidityZone[]>('/analysis/zones', { params: { symbol } });
  return res.data;
};

export const getSweepEvents = async (symbol: string): Promise<SweepEvent[]> => {
  const res = await apiClient.get<SweepEvent[]>('/analysis/sweeps', { params: { symbol } });
  return res.data;
};

export const getAnalysisOverview = async () => {
  const res = await apiClient.get<{ total_zones: number; active_zones: number; swept_zones: number; total_sweeps: number }>('/analysis/overview');
  return res.data;
};

export const getAnalysisStatus = async (symbol: string): Promise<AnalysisStatusData> => {
  const res = await apiClient.get<AnalysisStatusData>('/analysis/status', { params: { symbol } });
  return res.data;
};

