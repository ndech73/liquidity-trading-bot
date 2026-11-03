"""
test_idea8.py
-------------
Tests signal generation for Idea #8:
  1. Hand-checked Long signal: close[24] > close[0]
  2. Hand-checked Short signal: close[24] < close[0]
  3. No signal when close[24] == close[0]
  4. Time exclusion filter at 20:00, 21:00, 22:00 UTC
"""

import numpy as np
import pandas as pd
import pytest

from app.evaluation.idea8_signals import generate_idea8_signals


def make_h1_series(closes: list[float], start_time: str = "2024-01-01 10:00:00") -> pd.DataFrame:
    n = len(closes)
    times = pd.date_range(start_time, periods=n, freq="1h")
    return pd.DataFrame(
        {
            "time": times,
            "open": closes,
            "high": [c + 0.0010 for c in closes],
            "low": [c - 0.0010 for c in closes],
            "close": closes,
            "volume": np.ones(n) * 100,
            "spread": np.ones(n) * 10,
        }
    )


def test_hand_checked_long_signal():
    # 24 flat candles at 1.1000, then candle 24 closes at 1.1050 (> 1.1000)
    closes = [1.1000] * 24 + [1.1050]
    df = make_h1_series(closes, start_time="2024-01-01 02:00:00")
    sigs = generate_idea8_signals(df, lookback=24)

    assert len(sigs) == 25
    assert (sigs.iloc[:24] == 0).all()
    assert sigs.iloc[24] == 1  # Long


def test_hand_checked_short_signal():
    # 24 flat candles at 1.1000, then candle 24 closes at 1.0950 (< 1.1000)
    closes = [1.1000] * 24 + [1.0950]
    df = make_h1_series(closes, start_time="2024-01-01 02:00:00")
    sigs = generate_idea8_signals(df, lookback=24)

    assert len(sigs) == 25
    assert (sigs.iloc[:24] == 0).all()
    assert sigs.iloc[24] == -1  # Short


def test_equal_close_is_flat():
    closes = [1.1000] * 25
    df = make_h1_series(closes, start_time="2024-01-01 02:00:00")
    sigs = generate_idea8_signals(df, lookback=24)

    assert sigs.iloc[24] == 0


def test_utc_spread_spike_exclusion():
    # A candle that opens at 21:00 server time (winter, UTC+2) closes at 22:00 server = 20:00 UTC
    closes = [1.1000] * 24 + [1.1050]
    # Candle 24 opens at 21:00 server (closes at 22:00 server = 20:00 UTC)
    # Start time so candle 24 is at 21:00 server
    # 24 hours earlier is 21:00 the day before
    df = make_h1_series(closes, start_time="2024-01-01 21:00:00")
    sigs = generate_idea8_signals(df, lookback=24)

    # Candle 24 opens at 21:00 server, closes at 22:00 server = 20:00 UTC -> EXCLUDED
    assert sigs.iloc[24] == 0
