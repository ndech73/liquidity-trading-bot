"""
math_analyzer.py
----------------
A purely quantitative market analyzer built on 4 core mathematical foundations:
  1. Linear Algebra : Price series as vectors and matrices
  2. Statistics     : Rolling Mean (mu), Standard Deviation (sigma), and Z-Score
  3. Calculus       : First derivative (Velocity) and Second derivative (Acceleration)
  4. Probability    : Expected Value E[X] calculation including broker spread friction
"""

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------
# 1. Linear Algebra: Vector & Matrix Utilities
# ----------------------------------------------------------------------

def to_price_matrix(candles: pd.DataFrame) -> np.ndarray:
    """
    Extracts the OHLC price data as an N x 4 numerical matrix:
      Column 0: Open
      Column 1: High
      Column 2: Low
      Column 3: Close
    """
    required = ["open", "high", "low", "close"]
    return candles[required].to_numpy(dtype=float)


# ----------------------------------------------------------------------
# 2. Statistics: Mean, Standard Deviation & Z-Score
# ----------------------------------------------------------------------

def rolling_statistics(prices: pd.Series, window: int = 20) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculates the statistical distribution over a moving window:
      - mu (Mean)           : The central tendency (fair value)
      - sigma (Std Dev)     : The dispersion of prices
      - z_score             : Number of standard deviations away from the mean
                              Z = (Price - mu) / sigma
    """
    mu = prices.rolling(window=window).mean()
    sigma = prices.rolling(window=window).std()

    # Avoid division by zero
    z_score = (prices - mu) / sigma.replace(0, np.nan)
    return mu, sigma, z_score


# ----------------------------------------------------------------------
# 3. Calculus: Derivatives (Velocity & Acceleration)
# ----------------------------------------------------------------------

def price_derivatives(prices: pd.Series, step: int = 1) -> tuple[pd.Series, pd.Series]:
    """
    Calculates the discrete derivatives of price with respect to time:
      - Velocity (1st derivative, dP/dt)     : Rate of change of price (momentum).
      - Acceleration (2nd derivative, d2P/dt2): Rate of change of velocity.

    When velocity is large and positive, momentum is strong upward.
    When acceleration turns negative while velocity is positive,
    the upward momentum is slowing down (approaching a local extremum).
    """
    # First derivative: dP/dt
    velocity = prices.diff(periods=step) / step

    # Second derivative: d2P/dt2
    acceleration = velocity.diff(periods=step) / step

    return velocity, acceleration


# ----------------------------------------------------------------------
# 4. Probability: Mathematical Expectancy
# ----------------------------------------------------------------------

def expected_value(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    cost_per_trade: float = 0.0,
) -> float:
    """
    Calculates the Expected Value E[X] of a trading rule per trial:
      E[X] = (P_win * Avg_Win) - (P_loss * Avg_Loss) - Cost

    A trading strategy has a genuine statistical edge IF AND ONLY IF:
      E[X] > 0
    """
    loss_rate = 1.0 - win_rate
    raw_expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    net_expectancy = raw_expectancy - cost_per_trade
    return float(net_expectancy)


# ----------------------------------------------------------------------
# Unified Math Analysis Function
# ----------------------------------------------------------------------

def analyze_market_math(candles: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Applies the mathematical analysis to a candle series:
      Adds columns:
        - mu           : Rolling mean
        - sigma        : Rolling standard deviation
        - z_score      : Standardized price deviation
        - velocity     : 1st derivative (momentum)
        - acceleration : 2nd derivative (rate of momentum change)
    """
    df = candles.copy()
    close = df["close"]

    mu, sigma, z = rolling_statistics(close, window=window)
    vel, acc = price_derivatives(close, step=1)

    df["mu"] = mu
    df["sigma"] = sigma
    df["z_score"] = z
    df["velocity"] = vel
    df["acceleration"] = acc

    return df
