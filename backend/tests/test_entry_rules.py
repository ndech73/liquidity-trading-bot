"""
test_entry_rules.py
-------------------
Unit tests for mathematical entry signal generation on H1 and H4.
"""

import numpy as np
import pandas as pd
import pytest

from app.entry.entry_rules import (
    calculate_lot_size,
    detect_traps,
    generate_trap_signals,
    get_reference_boundaries,
)


def make_test_candles(n: int = 50) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01 00:00", periods=n, freq="1h")
    rng = np.random.default_rng(42)
    # Mean-reverting synthetic series around 1.1000
    noise = rng.normal(0, 0.0002, n)
    close = 1.1000 + noise

    return pd.DataFrame(
        {
            "time": dates,
            "open": close,
            "high": close + 0.0003,
            "low": close - 0.0003,
            "close": close,
            "volume": 200,
            "spread": 10,  # 10 points = 0.00010
        }
    )


def test_reference_boundaries_shift():
    candles = make_test_candles(30)
    p_high, p_low = get_reference_boundaries(candles, lookback=10)

    # First 10 rows (0 through 9) should be NaN due to lookback=10 and shift(1)
    assert pd.isna(p_high.iloc[0])
    assert pd.isna(p_high.iloc[9])
    assert not pd.isna(p_high.iloc[10])


def test_trap_detection():
    candles = make_test_candles(30)
    p_high = pd.Series(1.1010, index=candles.index)
    p_low = pd.Series(1.0990, index=candles.index)

    # Inject a bearish trap at index 15: poked above 1.1010, closed below
    candles.loc[15, "high"] = 1.1025
    candles.loc[15, "close"] = 1.1005

    bull, bear = detect_traps(candles, p_high, p_low)
    assert bear.iloc[15] == True
    assert bull.iloc[15] == False


def test_rollover_blackout_blocks_trade():
    candles = make_test_candles(50)
    # Set time to 22:00 UTC at candle 25
    candles.loc[25, "time"] = pd.Timestamp("2026-01-02 22:00:00")
    signals = generate_trap_signals(candles, symbol="EURUSD", lookback=10)

    # Rollover hour must always output 0
    assert signals.iloc[25] == 0


def test_calculate_lot_size():
    # Budget $3.50, stop 50 points -> 3.50 / 50 = 0.07 lots
    lot = calculate_lot_size(risk_budget_usd=3.50, stop_distance_points=50, symbol="EURUSD")
    assert lot == 0.07

    # Clamping tests
    min_lot = calculate_lot_size(risk_budget_usd=3.50, stop_distance_points=10000, symbol="EURUSD")
    assert min_lot == 0.01
