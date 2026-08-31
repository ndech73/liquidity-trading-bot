export type LiquidityType =
  | 'swing_high'
  | 'swing_low'
  | 'equal_high'
  | 'equal_low'
  | 'session_high'
  | 'session_low'
  | 'previous_high'
  | 'previous_low'

export type LiquidityStatus = 'active' | 'swept' | 'invalidated'

export interface LiquidityZone {
  id: string
  symbol: string
  timeframe: string
  price: number
  liquidityType: LiquidityType
  status: LiquidityStatus
  createdAt: string
  sweptAt?: string
  sweepPrice?: number
}
