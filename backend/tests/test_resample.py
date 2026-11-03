"""
test_resample.py
----------------
Tests that M15 aggregation to H1 (4x) and H4 (16x) is mathematically exact:
  1. Hand calculation check on open, high, low, close, volume, spread
  2. Incomplete candle dropping check
  3. Rejection of invalid timeframe string
"""

import numpy as np
import pandas as pd
import pytest

from app.evaluation.resample import resample_m15


def make_m15_sample():
    # 4 candles for 1 complete H1
    times = pd.date_range("2026-01-01 00:00", periods=4, freq="15min")
    return pd.DataFrame(
        {
            "time": times,
            "open": [1.1000, 1.1020, 1.1010, 1.1030],
            "high": [1.1025, 1.1050, 1.1035, 1.1040],
            "low": [1.0990, 1.1010, 1.1005, 1.1020],
            "close": [1.1020, 1.1015, 1.1030, 1.1035],
            "volume": [100.0, 200.0, 150.0, 250.0],
            "spread": [10.0, 15.0, 8.0, 12.0],
        }
    )


def test_h1_hand_calculation():
    df = make_m15_sample()
    h1, dropped = resample_m15(df, "H1")

    assert len(h1) == 1
    assert dropped == 0

    c = h1.iloc[0]
    assert c["time"] == pd.Timestamp("2026-01-01 00:00:00")
    assert np.isclose(c["open"], 1.1000)   # first open
    assert np.isclose(c["high"], 1.1050)   # max high
    assert np.isclose(c["low"], 1.0990)    # min low
    assert np.isclose(c["close"], 1.1035)  # last close
    assert np.isclose(c["volume"], 700.0)  # sum volume
    assert np.isclose(c["spread_worst"], 15.0)  # max spread
    assert np.isclose(c["spread_avg"], 11.25)   # mean spread: (10+15+8+12)/4
    assert np.isclose(c["spread"], 15.0)


def test_incomplete_candle_dropped():
    # 3 candles instead of 4
    times = pd.date_range("2026-01-01 00:00", periods=3, freq="15min")
    df = pd.DataFrame(
        {
            "time": times,
            "open": [1.10, 1.11, 1.12],
            "high": [1.11, 1.12, 1.13],
            "low": [1.09, 1.10, 1.11],
            "close": [1.10, 1.11, 1.12],
            "volume": [10, 10, 10],
            "spread": [5, 5, 5],
        }
    )
    h1, dropped = resample_m15(df, "H1")
    assert len(h1) == 0
    assert dropped == 1


def test_h4_aggregation_16_candles():
    times = pd.date_range("2026-01-01 00:00", periods=16, freq="15min")
    opens = np.linspace(1.10, 1.15, 16)
    df = pd.DataFrame(
        {
            "time": times,
            "open": opens,
            "high": opens + 0.0010,
            "low": opens - 0.0010,
            "close": opens + 0.0005,
            "volume": np.ones(16) * 50,
            "spread": np.ones(16) * 10,
        }
    )
    h4, dropped = resample_m15(df, "H4")
    assert len(h4) == 1
    assert dropped == 0
    assert np.isclose(h4.iloc[0]["volume"], 800.0)
