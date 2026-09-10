import { useState, useEffect, useCallback } from 'react';
import { getMarketList } from '../services/marketService';
import { MarketOverview } from '../types/market.types';
import { useWebSocket } from '../../../shared/hooks/useWebSocket';

export const useMarketData = () => {
  const [markets, setMarkets] = useState<MarketOverview[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('EURUSD');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lastMessage, isConnected } = useWebSocket<MarketOverview[]>('markets');

  // Real-time market quotes streaming via WebSocket
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'quotes' && Array.isArray(lastMessage.data)) {
      setMarkets(lastMessage.data);
      setIsLoading(false);
      setError(null);
    }
  }, [lastMessage]);

  const fetchMarkets = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getMarketList();
      setMarkets(res);
      if (res.length > 0 && !res.some((m) => m.symbol === selectedSymbol)) {
        setSelectedSymbol(res[0].symbol);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch market data from backend');
    } finally {
      setIsLoading(false);
    }
  }, [selectedSymbol]);

  useEffect(() => {
    fetchMarkets();
  }, [fetchMarkets]);

  return { markets, selectedSymbol, setSelectedSymbol, isLoading, error, refetch: fetchMarkets, isWsConnected: isConnected };
};

