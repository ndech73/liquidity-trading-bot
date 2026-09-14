export interface MarketConfig {
  symbol: string;
  name: string;
  category: 'Forex' | 'Crypto' | 'Indices';
  pipDecimalPlaces: number;
  minLotSize: number;
}

export const CHOSEN_WATCHLIST = ['EURJPY', 'USDCHF', 'NZDUSD', 'USDCAD', 'EURGBP'] as const;

export const DEFAULT_SYMBOL = 'EURJPY';

export const SUPPORTED_MARKETS: MarketConfig[] = [
  { symbol: 'EURJPY', name: 'EUR / JPY', category: 'Forex', pipDecimalPlaces: 2, minLotSize: 0.01 },
  { symbol: 'USDCHF', name: 'USD / CHF', category: 'Forex', pipDecimalPlaces: 4, minLotSize: 0.01 },
  { symbol: 'NZDUSD', name: 'NZD / USD', category: 'Forex', pipDecimalPlaces: 4, minLotSize: 0.01 },
  { symbol: 'USDCAD', name: 'USD / CAD', category: 'Forex', pipDecimalPlaces: 4, minLotSize: 0.01 },
  { symbol: 'EURGBP', name: 'EUR / GBP', category: 'Forex', pipDecimalPlaces: 4, minLotSize: 0.01 },
];
