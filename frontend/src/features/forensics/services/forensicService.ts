import { apiClient } from '../../../shared/services/apiClient';
import { ForensicRecord } from '../types/forensic.types';

export const getForensicRecords = async (): Promise<ForensicRecord[]> => {
  const res = await apiClient.get<ForensicRecord[]>('/forensics');
  return res.data;
};
