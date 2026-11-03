import numpy as np
import pandas as pd


# ----------------------------------------------------------------------
# 1. Linear Algebra: Vector & Matrix Utilities
# ----------------------------------------------------------------------

def to_price_matrix(candles: pd.DataFrame) -> np.ndarray:
    columns = ["open", "high", "low", "close"]
    return candles[columns].to_numpy(dtype=float)


# ----------------------------------------------------------------------
# 2. Statistics: Mean, Standard Deviation & Z-Score
# ----------------------------------------------------------------------

def rolling_statistics(prices: pd.Series, window: int = 20) -> tuple[pd.Series, pd.Series, pd.Series]:
    mu = prices.rolling(window=window).mean()
    sigma = prices.rolling(window=window).std()

    safe_sigma = sigma.replace(0, np.nan)
    z_score = (prices - mu) / safe_sigma

    return mu, sigma, z_score


# ----------------------------------------------------------------------
# 3. Calculus: Derivatives (Velocity & Acceleration)
# ----------------------------------------------------------------------

def price_derivatives(prices: pd.Series, step: int = 1) -> tuple[pd.Series, pd.Series]:
    velocity = prices.diff(periods=step) / step
    acceleration = velocity.diff(periods=step) / step

    return velocity, acceleration


# ----------------------------------------------------------------------
# 4. Time-Series: Direction Memory (Autocorrelation)
# ----------------------------------------------------------------------

def direction_memory(prices: pd.Series, window: int = 20) -> pd.Series:
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
    loss_rate = 1.0 - win_rate
    raw_payoff = (win_rate * avg_win) - (loss_rate * avg_loss)
    return float(raw_payoff - cost_per_trade)


# ----------------------------------------------------------------------
# 6. Unified Analyzer Orchestrator
# ----------------------------------------------------------------------

def analyze_market_math(candles: pd.DataFrame, window: int = 20) -> pd.DataFrame:
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