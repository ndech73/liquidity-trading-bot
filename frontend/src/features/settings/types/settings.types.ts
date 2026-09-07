export interface BotSettings {
  maxRiskPerTradePercent: number;
  maxOpenTrades: number;
  compressionThreshold: number;
  expansionThreshold: number;
  bridgeHost: string;
  bridgePort: number;
}
