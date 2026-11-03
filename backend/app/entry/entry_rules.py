"""
entry_rules.py
--------------
Generates trade signals (+1 Long, -1 Short, 0 Flat) using 4 mathematical filters:
  1. Z-Score (|z| >= z_threshold): Price is statistically stretched into extreme tails.
  2. Direction Memory (rho < 0)  : Market is in an elastic, mean-reverting regime.
  3. Acceleration (Calculus)    : Price movement has decelerated / exhausted.
  4. Toll Guard (Cost / ATR)    : Spread is small enough to guarantee positive expectancy.
"""

import numpy as np
import pandas as pd

from app.market_analyzer.math_analyzer import (
    direction_memory,
    price_derivatives,
    rolling_statistics,
)
from app.market_analyzer.volatility import atr


def generate_mean_reversion_signals(
    candles: pd.DataFrame,
    symbol: str,
    window: int = 20,
    z_threshold: float = 2.0,
    max_cost_ratio: float = 0.20,
) -> pd.Series:
    """
    Computes mathematical entry signals for each candle:
       +1 : Buy (Long) at the open of next candle
       -1 : Sell (Short) at the open of next candle
        0 : Do nothing (Flat)
    """
    n = len(candles)
    signals = np.zeros(n, dtype=int)

    # 1. Close Price Series
    closes = candles["close"]

    # 2. Statistics: Mean, Volatility (Ruler), and Z-Score (Rubber Band)
    mu, sigma, z_score = rolling_statistics(closes, window=window)

    # 3. Calculus: Velocity (Speed) and Acceleration (Brakes)
    velocity, acceleration = price_derivatives(closes, step=1)

    # 4. Time-Series: Direction Memory (Dog on Leash Check)
    memory = direction_memory(closes, window=window)

    # 5. Volatility Wave (ATR) & Spread Toll Guard
    atr_vals = atr(candles, period=14)
    point = 0.001 if "JPY" in symbol.upper() else 0.00001
    spread_points = candles["spread"] if "spread" in candles.columns else pd.Series(0.0, index=candles.index)
    cost_in_price = spread_points * point
    cost_ratio = cost_in_price / atr_vals.replace(0, np.nan)

    # Vectorized Mathematical Conditions
    # LONG SIGNAL:
    # - Price is stretched downwards (z <= -z_threshold)
    # - Market is elastic / leash is on (memory < 0)
    # - The fall is braking / decelerating (acceleration > 0)
    # - Spread fee is acceptable (cost_ratio <= max_cost_ratio)
    long_condition = (
        (z_score <= -z_threshold)
        & (memory < 0)
        & (acceleration > 0)
        & (cost_ratio <= max_cost_ratio)
    )

    # SHORT SIGNAL:
    # - Price is stretched upwards (z >= z_threshold)
    # - Market is elastic / leash is on (memory < 0)
    # - The surge is braking / decelerating (acceleration < 0)
    # - Spread fee is acceptable (cost_ratio <= max_cost_ratio)
    short_condition = (
        (z_score >= z_threshold)
        & (memory < 0)
        & (acceleration < 0)
        & (cost_ratio <= max_cost_ratio)
    )

    signals[long_condition.fillna(False)] = 1
    signals[short_condition.fillna(False)] = -1

    return pd.Series(signals, index=candles.index)


# ----------------------------------------------------------------------
# 6. Dynamic Position Sizing (Risk-Budget Lot Calculation)
# ----------------------------------------------------------------------

def calculate_lot_size(
    risk_budget_usd: float,
    stop_distance_points: float,
    symbol: str,
    min_lot: float = 0.01,
    max_lot: float = 10.0,
) -> float:
    """
    Calculates the exact lot size so dollar risk is ALWAYS identical:
      Lot_Size = Risk_Budget_USD / (Stop_Distance_Points * Pip_Value_USD)
    """
    if stop_distance_points <= 0:
        return min_lot

    # Standard pip value per 1.0 lot in MT5: ~10 USD per pip (100 points) on standard pairs
    # 1 point = 0.10 USD per standard lot
    usd_per_point_per_lot = 1.0 if "JPY" in symbol.upper() else 1.0  # approximate point value
    raw_lot = risk_budget_usd / (stop_distance_points * usd_per_point_per_lot)

    # Clamp between min_lot and max_lot, rounded to 2 decimals
    clamped_lot = max(min_lot, min(max_lot, raw_lot))
    return round(float(clamped_lot), 2)
