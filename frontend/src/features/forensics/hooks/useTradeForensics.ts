import { useState, useEffect, useCallback } from 'react';
import { getForensicRecords } from '../services/forensicService';
import { ForensicRecord } from '../types/forensic.types';

export const useTradeForensics = () => {
  const [records, setRecords] = useState<ForensicRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRecords = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getForensicRecords();
      setRecords(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch forensic records from backend');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords]);

  return { records, isLoading, error, refetch: fetchRecords };
};

