import { describe, it, expect } from 'vitest';
import { formatPrice } from '../../src/shared/utils/formatPrice';

describe('Trade Formatting', () => {
  it('formats trade prices with default 5 decimals', () => {
    expect(formatPrice(1.085023)).toBe('1.08502');
  });
});
