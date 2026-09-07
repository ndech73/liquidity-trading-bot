import { describe, it, expect } from 'vitest';
import { SUPPORTED_MARKETS } from '../../src/config/markets';

describe('Market Configuration', () => {
  it('includes major forex pairs', () => {
    const symbols = SUPPORTED_MARKETS.map((m) => m.symbol);
    expect(symbols).toContain('EURUSD');
    expect(symbols).toContain('GBPUSD');
  });
});
