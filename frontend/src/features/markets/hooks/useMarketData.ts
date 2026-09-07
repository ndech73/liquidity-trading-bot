import { useState, useEffect } from 'react';
import { getMarketList } from '../services/marketService';
import { MarketOverview } from '../types/market.types';

export const useMarketData = () => {
  const [markets, setMarkets] = useState<MarketOverview[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('EURUSD');

  useEffect(() => {
    getMarketList().then(setMarkets);
  }, []);

  return { markets, selectedSymbol, setSelectedSymbol };
};
