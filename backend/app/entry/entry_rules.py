"""
entry_rules.py
--------------
Generates trade signals (+1 Long, -1 Short, 0 Flat) from 24-hour
false-breakout traps.

Checkpoints:
  1. The 24-Hour Reference Fence (highest high / lowest low before this candle).
  2. The Breakout Trap Detector (poke outside the fence, close back inside).
  3. The Trampoline Shield (autocorrelation rho < 0).
  4. The Toll & Rollover Guard (spread <= 15% of ATR, no entries in blackout hours).
  5. Elastic Potential Check (optional: room to the opposite fence).
Helpers:
  6. calculate_invalidation_stop (stop at the trap candle's extreme).
  7. usd_per_point_per_lot and calculate_lot_size (size from a dollar risk budget).
"""

import math
from typing import Optional

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
    blackout_hours: tuple = (21, 22, 23),
) -> pd.Series:
    """
    Two checks, both must pass:
      - the spread is at most max_cost_ratio of ATR
      - the trade's ENTRY candle (the next candle) does not start in a
        blackout hour. Hours are broker SERVER time, the same clock as the
        'time' column. Set them from the spread-by-hour check on your data.

    It only reads the next candle's clock time, never its prices.
    """
    if "spread" not in candles.columns:
        raise ValueError("candles need a 'spread' column for the cost guard")
    if "time" not in candles.columns:
        raise ValueError("candles need a 'time' column for the blackout guard")

    atr_vals = atr(candles, period=14)
    cost_in_price = candles["spread"] * point_size(symbol)

    cost_ratio = cost_in_price / atr_vals.replace(0, np.nan)
    fee_is_small = cost_ratio <= max_cost_ratio

    # The trade enters at the open of the NEXT candle, so check that hour.
    entry_hour = candles["time"].shift(-1).dt.hour
    not_blackout = ~entry_hour.isin(list(blackout_hours))

    return fee_is_small & not_blackout


# ----------------------------------------------------------------------
# 5. Corridor Elastic Potential (Minimum Full-Swing Space)
# ----------------------------------------------------------------------

def check_sufficient_stretch(
    candles: pd.DataFrame,
    prior_high: pd.Series,
    prior_low: pd.Series,
    min_span_atr: float = 1.0,
) -> tuple[pd.Series, pd.Series]:
    """
    Only take a trade if there is enough room to the opposite fence:
      - Long  (+1) : (prior_high - close) / ATR >= min_span_atr
      - Short (-1) : (close - prior_low) / ATR >= min_span_atr
    This filters out trades in narrow, compressed corridors.
    """
    atr_vals = atr(candles, period=14).replace(0, np.nan)
    closes = candles["close"]

    long_span = (prior_high - closes) / atr_vals
    short_span = (closes - prior_low) / atr_vals

    return (long_span >= min_span_atr), (short_span >= min_span_atr)


# ----------------------------------------------------------------------
# 6. Master Entry Signal Engine
# ----------------------------------------------------------------------

def generate_trap_signals(
    candles: pd.DataFrame,
    symbol: str,
    lookback: int = 24,
    max_cost_ratio: float = 0.15,
    min_span_atr: float = 0.0,
    blackout_hours: tuple = (21, 22, 23),
) -> pd.Series:
    """
    Unified Entry Engine for H1 and H4:
      - lookback = 24 for H1 (1 full day)
      - lookback = 6  for H4 (1 full day)
      - min_span_atr = minimum room to the opposite fence, in ATR (0 = off)
    """
    # 1. 24-hour reference fence
    prior_high, prior_low = get_reference_boundaries(candles, lookback=lookback)

    # 2. Breakout trap detection
    bullish_trap, bearish_trap = detect_traps(candles, prior_high, prior_low)

    # 3. Market regime shield (rho < 0)
    valid_long, valid_short = filter_by_market_regime(
        candles, bullish_trap, bearish_trap, lookback=lookback
    )

    # 4. A candle that pokes BOTH fences gives two opposite signals: skip it.
    both = valid_long & valid_short
    valid_long = valid_long & ~both
    valid_short = valid_short & ~both

    # 5. Elastic potential check (room to the opposite fence)
    if min_span_atr > 0.0:
        has_long_span, has_short_span = check_sufficient_stretch(
            candles, prior_high, prior_low, min_span_atr=min_span_atr
        )
        valid_long = valid_long & has_long_span
        valid_short = valid_short & has_short_span

    # 6. Cost toll & rollover guard
    cheap_fee = is_fee_cheap(
        candles, symbol, max_cost_ratio=max_cost_ratio, blackout_hours=blackout_hours
    )

    # 7. Stamp signals (+1 Long, -1 Short, 0 Flat)
    signals = pd.Series(0, index=candles.index, dtype=int)
    signals[valid_long & cheap_fee] = 1
    signals[valid_short & cheap_fee] = -1

    return signals


# ----------------------------------------------------------------------
# 7. Structural Thesis Invalidation (The Natural Stop Level)
# ----------------------------------------------------------------------

def calculate_invalidation_stop(
    direction: int,
    signal_candle: pd.Series,
    current_atr: float,
    buffer_atr: float = 0.1,
    entry_price: Optional[float] = None,
) -> Optional[float]:
    """
    The price where the trap idea is proven wrong:
      - Long  (+1): below the trap candle's low (minus a small buffer)
      - Short (-1): above the trap candle's high (plus a small buffer)

    If entry_price is given and the stop is already on the wrong side of it
    (price gapped past the stop), returns None. Skip that trade.
    """
    if direction not in (1, -1):
        raise ValueError(f"Direction must be +1 or -1, got {direction}")
    if not current_atr > 0:  # also catches NaN
        raise ValueError("ATR must be above 0 to place a stop")

    buffer_dist = buffer_atr * current_atr

    if direction == 1:
        stop = float(signal_candle["low"] - buffer_dist)
        if entry_price is not None and stop >= entry_price:
            return None
    else:
        stop = float(signal_candle["high"] + buffer_dist)
        if entry_price is not None and stop <= entry_price:
            return None

    return stop


# ----------------------------------------------------------------------
# 8. Dynamic Position Sizing (Risk-Budget Lot Calculation)
# ----------------------------------------------------------------------

def usd_per_point_per_lot(
    symbol: str,
    quote_to_usd_rate: Optional[float] = None,
    contract_size: int = 100_000,
) -> float:
    """
    Dollar value of ONE point for ONE lot.
      - USD-quoted pairs (EURUSD, GBPUSD, NZDUSD): rate is 1, so $1.00 per point.
      - Other pairs (USDCAD, USDCHF, EURJPY): the value is first in CAD, CHF
        or JPY, so you must pass quote_to_usd_rate (for example, the current
        USD value of 1 CAD).
    Check your account's contract size in MT5 (normally 100,000).
    """
    quote_currency = symbol.upper()[3:6]
    if quote_currency == "USD":
        rate = 1.0
    elif quote_to_usd_rate is None:
        raise ValueError(
            f"{symbol} is quoted in {quote_currency}: pass quote_to_usd_rate "
            f"(the USD value of 1 {quote_currency})"
        )
    else:
        rate = quote_to_usd_rate

    return contract_size * point_size(symbol) * rate


def calculate_lot_size(
    risk_budget_usd: float,
    stop_distance_points: float,
    symbol: str,
    quote_to_usd_rate: Optional[float] = None,
    min_lot: float = 0.01,
    max_lot: float = 10.0,
    lot_step: float = 0.01,
) -> float:
    """
    Lot size so the dollar loss at the stop is at most the risk budget:
      lots = budget / (stop distance in points x $ per point per lot)

    Rounds DOWN to the lot step. Returns 0.0 (skip the trade) when even the
    smallest lot would risk more than the budget, or when inputs are invalid.
    """
    if not risk_budget_usd > 0 or not stop_distance_points > 0:
        return 0.0

    risk_per_lot = stop_distance_points * usd_per_point_per_lot(symbol, quote_to_usd_rate)
    raw_lot = risk_budget_usd / risk_per_lot
    lot = round(math.floor(raw_lot / lot_step + 1e-9) * lot_step, 2)

    if lot < min_lot:
        return 0.0  # the smallest lot already risks more than the budget

    return round(min(lot, max_lot), 2)