import { useState, useEffect, useCallback } from 'react';
import { getActiveTrades } from '../services/tradeService';
import { ActiveTrade } from '../types/trade.types';
import { useWebSocket } from '../../../shared/hooks/useWebSocket';

export const useTrades = () => {
  const [trades, setTrades] = useState<ActiveTrade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lastMessage, isConnected } = useWebSocket<ActiveTrade[]>('trades');

  // Real-time trades updates via WebSocket relay
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'update' && Array.isArray(lastMessage.data)) {
      setTrades(lastMessage.data);
      setIsLoading(false);
      setError(null);
    }
  }, [lastMessage]);

  const fetchTrades = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getActiveTrades();
      setTrades(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch active trades from backend');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  return { trades, isLoading, error, refetch: fetchTrades, isWsConnected: isConnected };
};

