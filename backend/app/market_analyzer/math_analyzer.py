"""
math_analyzer.py
----------------
A purely quantitative market analyzer built on mathematical foundations:
  1. Linear Algebra : Price series as vectors and matrices
  2. Statistics     : Rolling Mean (mu), Standard Deviation (sigma), and Z-Score (z)
  3. Calculus       : First derivative (Velocity) and Second derivative (Acceleration)
  4. Time-Series    : Serial correlation (Direction memory: Trampoline vs. Waterfall)
  5. Probability    : Expected Value E[X] after broker spread friction
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
    columns = ["open", "high", "low", "close"]
    return candles[columns].to_numpy(dtype=float)


# ----------------------------------------------------------------------
# 2. Statistics: Mean, Standard Deviation & Z-Score
# ----------------------------------------------------------------------

def rolling_statistics(
    prices: pd.Series, window: int = 24
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculates the statistical distribution over a moving window:
      - mu (Mean)           : The central tendency (fair value anchor)
      - sigma (Std Dev)     : The dispersion (our measuring ruler)
      - z_score             : How many rulers the price is stretched (rubber band)
    """
    mu = prices.rolling(window=window).mean()
    sigma = prices.rolling(window=window).std()

    # Avoid division by zero if sigma is ever 0
    safe_sigma = sigma.replace(0, np.nan)
    z_score = (prices - mu) / safe_sigma

    return mu, sigma, z_score


# ----------------------------------------------------------------------
# 3. Calculus: Derivatives (Velocity & Acceleration)
# ----------------------------------------------------------------------

def price_derivatives(
    prices: pd.Series, step: int = 1
) -> tuple[pd.Series, pd.Series]:
    """
    Calculates the rate of change of price with respect to time:
      - Velocity (1st derivative, dP/dt)     : Speed and direction of price movement.
      - Acceleration (2nd derivative, d2P/dt2): Rate of change of velocity (exhaustion/brakes).
    """
    # First derivative: rate of change (speed)
    velocity = prices.diff(periods=step) / step

    # Second derivative: rate of speed change (acceleration)
    acceleration = velocity.diff(periods=step) / step

    return velocity, acceleration


# ----------------------------------------------------------------------
# 4. Time-Series: Direction Memory (Autocorrelation)
# ----------------------------------------------------------------------

def direction_memory(prices: pd.Series, window: int = 24) -> pd.Series:
    """
    Calculates the correlation between the current change and previous change:
      - Negative value (< 0): Trampoline. Price tends to bounce back (Mean Reversion).
      - Positive value (> 0): Waterfall. Price tends to keep running (Momentum).
    """
    returns = prices.pct_change()
    lagged_returns = returns.shift(1)
    return returns.rolling(window=window).corr(lagged_returns)


# ----------------------------------------------------------------------
# 5. Probability: Expected Value Net of Broker Cost
# ----------------------------------------------------------------------

def expected_value(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    cost_per_trade: float = 0.0,
) -> float:
    """
    Calculates the true Expected Value E[X] after broker spread deduction:
      E[X] = (Win_Probability * Avg_Win) - (Loss_Probability * Avg_Loss) - Cost
    A viable trading edge requires E[X] > 0 and Net Profit >= 2x to 3x Cost.
    """
    loss_rate = 1.0 - win_rate
    raw_payoff = (win_rate * avg_win) - (loss_rate * avg_loss)
    return float(raw_payoff - cost_per_trade)


# ----------------------------------------------------------------------
# 6. Unified Analyzer Orchestrator
# ----------------------------------------------------------------------

def analyze_market_math(
    candles: pd.DataFrame, window: int = 24
) -> pd.DataFrame:
    """
    Takes raw candle data and outputs a complete mathematical analysis table:
      - mu           : 24-period center of mass
      - sigma        : 24-period ruler size
      - z_score      : Current rubber band tension
      - velocity     : Current price speed
      - acceleration : Whether the speed is speeding up or braking
      - memory       : Whether the market is a Trampoline or a Waterfall
    """
    df = candles.copy()
    close = df["close"]

    mu, sigma, z = rolling_statistics(close, window=window)
    vel, acc = price_derivatives(close, step=1)
    mem = direction_memory(close, window=window)

    df["mu"] = mu
    df["sigma"] = sigma
    df["z_score"] = z
    df["velocity"] = vel
    df["acceleration"] = acc
    df["memory"] = mem

    return df