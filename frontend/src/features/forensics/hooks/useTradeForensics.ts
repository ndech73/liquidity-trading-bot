import { useState, useEffect } from 'react';
import { getForensicRecords } from '../services/forensicService';
import { ForensicRecord } from '../types/forensic.types';

export const useTradeForensics = () => {
  const [records, setRecords] = useState<ForensicRecord[]>([]);

  useEffect(() => {
    getForensicRecords().then(setRecords);
  }, []);

  return { records };
};
