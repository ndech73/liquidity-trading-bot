import { useState, useEffect, useCallback } from 'react';
import { getAccountInfo, AccountInfo } from '../services/accountService';
import { useWebSocket } from './useWebSocket';

export const useAccount = () => {
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lastMessage, isConnected } = useWebSocket<AccountInfo>('account');

  // Instant real-time updates via WebSocket relay
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'update' && lastMessage.data) {
      setAccount(lastMessage.data);
      setIsLoading(false);
      setError(null);
    }
  }, [lastMessage]);

  const fetchAccount = useCallback(async () => {
    try {
      const data = await getAccountInfo();
      setAccount(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch account status');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAccount();
    const interval = setInterval(fetchAccount, 10000);
    return () => clearInterval(interval);
  }, [fetchAccount]);

  return { account, isLoading, error, refetch: fetchAccount, isWsConnected: isConnected };
};

