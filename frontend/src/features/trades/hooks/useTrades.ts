import { useState, useEffect } from 'react';
import { getActiveTrades } from '../services/tradeService';
import { ActiveTrade } from '../types/trade.types';

export const useTrades = () => {
  const [trades, setTrades] = useState<ActiveTrade[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getActiveTrades().then((res) => {
      setTrades(res);
      setIsLoading(false);
    });
  }, []);

  return { trades, isLoading };
};
