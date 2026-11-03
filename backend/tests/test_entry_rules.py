"""
test_entry_rules.py
-------------------
Unit tests for mathematical entry signal generation.
"""

import numpy as np
import pandas as pd
import pytest

from app.entry.entry_rules import generate_mean_reversion_signals


def make_test_candles(n: int = 50) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    rng = np.random.default_rng(42)
    # Mean-reverting synthetic series around 1.1000
    noise = rng.normal(0, 0.0002, n)
    close = 1.1000 + noise
    # Insert an extreme downward stretch at index 35
    close[35] = 1.0950
    # Next candle slows down (acceleration turns positive)
    close[36] = 1.0952

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


def test_signal_output_shape_and_values():
    candles = make_test_candles(50)
    signals = generate_mean_reversion_signals(candles, symbol="EURUSD", window=20, z_threshold=1.5)

    assert len(signals) == 50
    # Values can only be +1, -1, or 0
    assert set(signals.unique()).issubset({-1, 0, 1})


def test_toll_guard_blocks_expensive_spread():
    candles = make_test_candles(50)
    # Set exorbitant spread: 500 points (50 pips)
    candles["spread"] = 500

    signals = generate_mean_reversion_signals(candles, symbol="EURUSD", max_cost_ratio=0.10)
    # Toll guard should block all entries due to excessive cost
    assert (signals != 0).sum() == 0
