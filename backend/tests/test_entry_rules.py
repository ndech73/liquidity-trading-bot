"""
test_entry_rules.py
-------------------
Unit tests for mathematical entry signal generation on H1 and H4.
"""

import numpy as np
import pandas as pd
import pytest

from app.entry.entry_rules import (
    calculate_invalidation_stop,
    calculate_lot_size,
    check_sufficient_stretch,
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
    assert min_lot == 0.0


def test_calculate_invalidation_stop():
    candle = pd.Series({"high": 1.1050, "low": 1.0950, "close": 1.1000})
    atr_val = 0.0050

    # For Long (+1): stop = low - 0.1 * atr = 1.0950 - 0.0005 = 1.0945
    long_stop = calculate_invalidation_stop(direction=1, signal_candle=candle, current_atr=atr_val, buffer_atr=0.1)
    assert pytest.approx(long_stop, abs=1e-6) == 1.0945

    # For Short (-1): stop = high + 0.1 * atr = 1.1050 + 0.0005 = 1.1055
    short_stop = calculate_invalidation_stop(direction=-1, signal_candle=candle, current_atr=atr_val, buffer_atr=0.1)
    assert pytest.approx(short_stop, abs=1e-6) == 1.1055


def test_check_sufficient_stretch():
    candles = make_test_candles(30)
    # Give candles an ATR around 0.0010
    prior_high = pd.Series(1.1050, index=candles.index)  # wide ceiling
    prior_low = pd.Series(1.0950, index=candles.index)   # wide floor

    # Candle 15 close is 1.1000:
    # Distance to ceiling = 1.1050 - 1.1000 = 0.0050 (~8x ATR) -> True
    # Distance to floor = 1.1000 - 1.0950 = 0.0050 (~8x ATR) -> True
    long_ok, short_ok = check_sufficient_stretch(candles, prior_high, prior_low, min_span_atr=1.0)
    assert bool(long_ok.iloc[15]) is True
    assert bool(short_ok.iloc[15]) is True

    # If ceiling is extremely tight (1.1001 vs close 1.1000):
    tight_high = pd.Series(1.1001, index=candles.index)
    long_ok_tight, _ = check_sufficient_stretch(candles, tight_high, prior_low, min_span_atr=1.0)
    assert bool(long_ok_tight.iloc[15]) is False
