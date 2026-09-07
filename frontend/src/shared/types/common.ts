export type Timeframe = 'M1' | 'M5' | 'M15' | 'H1' | 'H4' | 'D1';

export type TrendDirection = 'BULLISH' | 'BEARISH' | 'NEUTRAL';

export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt?: string;
}

export interface PaginationParams {
  page: number;
  limit: number;
}
