import { describe, it, expect } from 'vitest';
import { formatPercentage } from '../../src/shared/utils/formatPercentage';

describe('Performance Utils', () => {
  it('formats positive percentage with plus prefix', () => {
    expect(formatPercentage(5.2)).toBe('+5.20%');
  });
});
