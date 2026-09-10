import { useState, useEffect, useCallback } from 'react';
import { getLiquidityZones, getSweepEvents, getAnalysisStatus } from '../services/analysisService';
import { LiquidityZone, SweepEvent, AnalysisStatusData } from '../types/analysis.types';

export const useAnalysis = (symbol: string) => {
  const [zones, setZones] = useState<LiquidityZone[]>([]);
  const [sweeps, setSweeps] = useState<SweepEvent[]>([]);
  const [status, setStatus] = useState<AnalysisStatusData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysis = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [z, s, st] = await Promise.all([
        getLiquidityZones(symbol),
        getSweepEvents(symbol),
        getAnalysisStatus(symbol),
      ]);
      setZones(z);
      setSweeps(s);
      setStatus(st);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch analysis data from backend');
    } finally {
      setIsLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    fetchAnalysis();
  }, [fetchAnalysis]);

  return { zones, sweeps, status, isLoading, error, refetch: fetchAnalysis };
};

