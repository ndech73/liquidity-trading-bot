import { apiClient } from './apiClient';

export interface AccountInfo {
  login: number | null;
  balance: number;
  equity: number;
  currency: string;
  connected: boolean;
  status: 'RUNNING' | 'PAUSED' | 'OFFLINE';
  open_trades_count: number;
  unrealized_pnl: number;
}

export const getAccountInfo = async (): Promise<AccountInfo> => {
  const res = await apiClient.get<AccountInfo>('/account');
  return res.data;
};
