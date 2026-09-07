import { useState, useEffect } from 'react';
import { getLiquidityZones, getSweepEvents } from '../services/analysisService';
import { LiquidityZone, SweepEvent } from '../types/analysis.types';

export const useAnalysis = (symbol: string) => {
  const [zones, setZones] = useState<LiquidityZone[]>([]);
  const [sweeps, setSweeps] = useState<SweepEvent[]>([]);

  useEffect(() => {
    getLiquidityZones(symbol).then(setZones);
    getSweepEvents(symbol).then(setSweeps);
  }, [symbol]);

  return { zones, sweeps };
};
