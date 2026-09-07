import { BotSettings } from '../types/settings.types';

export const getBotSettings = async (): Promise<BotSettings> => {
  return {
    maxRiskPerTradePercent: 1.0,
    maxOpenTrades: 5,
    compressionThreshold: 0.70,
    expansionThreshold: 1.50,
    bridgeHost: '127.0.0.1',
    bridgePort: 18812,
  };
};
