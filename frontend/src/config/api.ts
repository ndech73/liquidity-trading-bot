import { ENV } from './env';

export const API_ENDPOINTS = {
  HEALTH: `${ENV.API_URL}/health`,
  ACCOUNT: `${ENV.API_URL}/account`,
  MARKETS: `${ENV.API_URL}/markets`,
  TRADES: `${ENV.API_URL}/trades`,
  ANALYSIS: `${ENV.API_URL}/analysis`,
  FORENSICS: `${ENV.API_URL}/forensics`,
  PERFORMANCE: `${ENV.API_URL}/performance`,
  SETTINGS: `${ENV.API_URL}/settings`,
} as const;

export const WS_CHANNELS = {
  TRADES: 'trades',
  PRICES: 'prices',
  LIQUIDITY_EVENTS: 'liquidity_events',
  SYSTEM_STATUS: 'system_status',
} as const;
