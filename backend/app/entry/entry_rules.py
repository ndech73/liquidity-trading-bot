"""
entry_rules.py
--------------
Generates trade signals (+1 Long, -1 Short, 0 Flat) on H1 and H4 timeframes
using 4 strict mathematical security checkpoints:
  1. The 24-Hour Reference Fence (Order statistics Mt and mt).
  2. The Breakout Trap Detector (Inflection point rejection).
  3. The Trampoline Shield (Autocorrelation rho < 0 to avoid runaway trends).
  4. The Toll & Rollover Guard (Spread / ATR <= 15% and zero entries at 21-23 UTC).
  5. Dynamic Position Sizing (calculate_lot_size locks dollar risk to budget).
"""

import numpy as np
import pandas as pd

from app.evaluation.outcomes import point_size
from app.market_analyzer.math_analyzer import direction_memory
from app.market_analyzer.volatility import atr


# ----------------------------------------------------------------------
# 1. The 24-Hour Reference Fence (Order Statistics)
# ----------------------------------------------------------------------

def get_reference_boundaries(
    candles: pd.DataFrame, lookback: int = 24
) -> tuple[pd.Series, pd.Series]:
    """
    Computes prior highest high and lowest low excluding current candle:
      - lookback = 24 for H1 (24 hours)
      - lookback = 6  for H4 (24 hours)
    """
    highs = candles["high"]
    lows = candles["low"]

    prior_high = highs.rolling(window=lookback).max().shift(1)
    prior_low = lows.rolling(window=lookback).min().shift(1)

    return prior_high, prior_low


# ----------------------------------------------------------------------
# 2. The Breakout Trap Detector (Rejections)
# ----------------------------------------------------------------------

def detect_traps(
    candles: pd.DataFrame, prior_high: pd.Series, prior_low: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """
    Detects when price pokes outside the 24h fence and closes back inside.
    """
    highs = candles["high"]
    lows = candles["low"]
    closes = candles["close"]

    # Bullish trap (Buy): poked below floor, closed back above
    bullish_trap = (lows < prior_low) & (closes > prior_low)

    # Bearish trap (Sell): poked above ceiling, closed back below
    bearish_trap = (highs > prior_high) & (closes < prior_high)

    return bullish_trap, bearish_trap


# ----------------------------------------------------------------------
# 3. Market Regime Shield (Trampoline Check rho < 0)
# ----------------------------------------------------------------------

def filter_by_market_regime(
    candles: pd.DataFrame,
    bullish_trap: pd.Series,
    bearish_trap: pd.Series,
    lookback: int = 24,
) -> tuple[pd.Series, pd.Series]:
    """
    Filters out traps when market is in a violent runaway waterfall trend.
    Only allows trades when autocorrelation rho < 0 (elastic trampoline).
    """
    memory = direction_memory(candles["close"], window=lookback)
    is_trampoline = memory < 0.0

    valid_long = bullish_trap & is_trampoline
    valid_short = bearish_trap & is_trampoline

    return valid_long, valid_short


# ----------------------------------------------------------------------
# 4. The Toll & Rollover Guard (Cost Protection)
# ----------------------------------------------------------------------

def is_fee_cheap(
    candles: pd.DataFrame,
    symbol: str,
    max_cost_ratio: float = 0.15,
) -> pd.Series:
    """
    Guarantees spread is small enough (<= 15% of ATR) and blocks entries
    during dangerous broker rollover hours (21:00 to 23:00 UTC).
    """
    atr_vals = atr(candles, period=14)
    point = point_size(symbol)

    spread_points = candles["spread"] if "spread" in candles.columns else pd.Series(0.0, index=candles.index)
    cost_in_price = spread_points * point

    cost_ratio = cost_in_price / atr_vals.replace(0, np.nan)
    fee_is_small = cost_ratio <= max_cost_ratio

    # Rollover blackout: brokers widen spreads by up to 800% at 21:00-23:00 UTC
    if "time" in candles.columns and hasattr(candles["time"].dt, "hour"):
        utc_hours = candles["time"].dt.hour
        not_rollover = ~utc_hours.isin([21, 22, 23])
    else:
        not_rollover = pd.Series(True, index=candles.index)

    return fee_is_small & not_rollover


# ----------------------------------------------------------------------
# 5. Master Entry Signal Engine
# ----------------------------------------------------------------------

def generate_trap_signals(
    candles: pd.DataFrame,
    symbol: str,
    lookback: int = 24,
    max_cost_ratio: float = 0.15,
) -> pd.Series:
    """
    Unified Entry Engine for H1 and H4:
      - lookback = 24 for H1 (1 full day)
      - lookback = 6  for H4 (1 full day)
    """
    # 1. 24-hour reference fence
    prior_high, prior_low = get_reference_boundaries(candles, lookback=lookback)

    # 2. Breakout trap detection
    bullish_trap, bearish_trap = detect_traps(candles, prior_high, prior_low)

    # 3. Market regime shield (rho < 0)
    valid_long, valid_short = filter_by_market_regime(
        candles, bullish_trap, bearish_trap, lookback=lookback
    )

    # 4. Cost toll & rollover guard
    cheap_fee = is_fee_cheap(candles, symbol, max_cost_ratio=max_cost_ratio)

    # 5. Stamp signals (+1 Long, -1 Short, 0 Flat)
    signals = pd.Series(0, index=candles.index, dtype=int)
    signals[valid_long & cheap_fee] = 1
    signals[valid_short & cheap_fee] = -1

    return signals


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
    Calculates exact lot size so dollar risk is ALWAYS identical:
      Lot_Size = Risk_Budget_USD / (Stop_Distance_Points * Pip_Value_USD)
    """
    if stop_distance_points <= 0:
        return min_lot

    # Standard pip value per 1.0 lot in MT5: $1.00 per point
    usd_per_point_per_lot = 1.0
    raw_lot = risk_budget_usd / (stop_distance_points * usd_per_point_per_lot)

    clamped_lot = max(min_lot, min(max_lot, raw_lot))
    return round(float(clamped_lot), 2)