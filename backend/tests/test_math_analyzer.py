"""
test_math_analyzer.py
---------------------
Tests the mathematical operations in math_analyzer.py:
  1. Matrix conversion (Linear Algebra)
  2. Rolling statistics & Z-Score (Statistics)
  3. Derivatives (Calculus)
  4. Expected Value (Probability)
"""

import numpy as np
import pandas as pd
import pytest

from app.market_analyzer.math_analyzer import (
    analyze_market_math,
    expected_value,
    price_derivatives,
    rolling_statistics,
    to_price_matrix,
)


def sample_candles() -> pd.DataFrame:
    n = 30
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    prices = np.linspace(1.1000, 1.1060, n)
    return pd.DataFrame(
        {
            "time": dates,
            "open": prices,
            "high": prices + 0.0005,
            "low": prices - 0.0005,
            "close": prices + 0.0002,
        }
    )


def test_linear_algebra_matrix_conversion():
    df = sample_candles()
    mat = to_price_matrix(df)
    assert isinstance(mat, np.ndarray)
    assert mat.shape == (30, 4)
    assert np.isclose(mat[0, 0], 1.1000)


def test_statistics_rolling():
    s = pd.Series([10.0, 10.0, 10.0, 10.0, 10.0])
    mu, sigma, z = rolling_statistics(s, window=3)
    assert np.isclose(mu.iloc[4], 10.0)
    assert np.isclose(sigma.iloc[4], 0.0)


def test_calculus_derivatives():
    # Linear price growth: P(t) = 2*t
    # First derivative (velocity) should be constant = 2.0
    # Second derivative (acceleration) should be 0.0
    s = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
    vel, acc = price_derivatives(s, step=1)
    assert np.isclose(vel.iloc[2], 2.0)
    assert np.isclose(acc.iloc[2], 0.0)


def test_probability_expected_value():
    # 50% win rate, win = 2.0 ATR, loss = 1.0 ATR, cost = 0.2 ATR
    # E[X] = (0.5 * 2.0) - (0.5 * 1.0) - 0.2 = 1.0 - 0.5 - 0.2 = +0.3 ATR
    ev = expected_value(win_rate=0.50, avg_win=2.0, avg_loss=1.0, cost_per_trade=0.2)
    assert np.isclose(ev, 0.30)
