import { describe, it, expect } from 'vitest';
import { calculateTotalPnL, calculateWinRate } from '../../src/features/dashboard/utils/dashboardCalculations';

describe('Dashboard Calculations', () => {
  it('calculates total PnL accurately', () => {
    const days = [{ date: 'Mon', pnl: 50, tradesCount: 2 }, { date: 'Tue', pnl: -20, tradesCount: 1 }];
    expect(calculateTotalPnL(days)).toBe(30);
  });

  it('calculates win rate correctly', () => {
    expect(calculateWinRate(3, 4)).toBe(75);
    expect(calculateWinRate(0, 0)).toBe(0);
  });
});
