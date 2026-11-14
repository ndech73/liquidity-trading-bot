"""
exit_rules.py
-------------
Exit rules for an open trade, checked once per candle, in this order:
  1. Stop loss  : checked FIRST. If a candle touches the stop, the trade is
                  stopped, even if the same candle later closes at the target.
  2. Target     : z-score reaches the target (0 = back at the average).
  3. Time limit : the trade has been open for max_bars candles.

NOT implemented: break-even stops and trailing stops. Adding either is a new
setting and must be written in the rules file before any test uses it.

Prices are candle prices (bid side). Target exits are filled at the candle's
close, which is slightly optimistic: real fills happen a moment later.
"""

import math
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    exit_price: float
    exit_reason: str  # "stop_loss", "target_equilibrium", "target_full_swing", "time_limit"


# ----------------------------------------------------------------------
# 1. Stop Loss Exit (checked FIRST)
# ----------------------------------------------------------------------

def check_stop_loss_exit(
    direction: int,
    entry_price: float,
    current_high: float,
    current_low: float,
    current_atr: float,
    stop_loss_atr: float = 1.5,
    stop_price: Optional[float] = None,
    current_open: Optional[float] = None,
) -> Optional[ExitDecision]:
    """
    Stops the trade if the candle touched the stop price.
      - Long  (+1): the candle's low is at or below the stop.
      - Short (-1): the candle's high is at or above the stop.
    If the candle OPENED past the stop (a gap), the fill is the open, which
    is worse than the stop. Pass current_open so gaps are handled.
    If stop_price is not given, the stop is stop_loss_atr x ATR from entry.
    """
    if direction not in (1, -1):
        raise ValueError(f"direction must be +1 or -1, got {direction}")

    if stop_price is None:
        if not current_atr > 0:  # also catches NaN
            raise ValueError("ATR must be above 0 to place a stop")
        stop_price = entry_price - direction * stop_loss_atr * current_atr

    if math.isnan(stop_price):
        raise ValueError("stop_price is NaN")

    if direction == 1 and current_low <= stop_price:
        fill = stop_price if current_open is None else min(current_open, stop_price)
    elif direction == -1 and current_high >= stop_price:
        fill = stop_price if current_open is None else max(current_open, stop_price)
    else:
        return None

    return ExitDecision(
        should_exit=True,
        exit_price=float(fill),
        exit_reason="stop_loss",
    )


# ----------------------------------------------------------------------
# 2. Target Exit: Equilibrium (z = 0) or Full Swing (z beyond target_z)
# ----------------------------------------------------------------------

def check_target_exit(
    direction: int,
    current_close: float,
    current_z_score: float,
    target_z: float = 0.0,
) -> Optional[ExitDecision]:
    """
    Takes profit when the z-score reaches the target:
      - Long  (+1): exit when z >= target_z
      - Short (-1): exit when z <= -target_z
      - target_z = 0.0 : price is back at its recent average (equilibrium)
      - target_z > 0.0 : price went on to the other side (full swing)

    Note: the z-score uses a moving average that slides with price, so "z
    reached 0" does not always mean price moved in your favour.
    """
    if direction not in (1, -1):
        raise ValueError(f"direction must be +1 or -1, got {direction}")
    if target_z < 0:
        raise ValueError(f"target_z must be 0 or more, got {target_z}")

    # Not enough history to calculate z yet: no target signal.
    if math.isnan(current_z_score):
        return None

    reason = "target_full_swing" if target_z > 0.0 else "target_equilibrium"

    if direction == 1 and current_z_score >= target_z:
        return ExitDecision(should_exit=True, exit_price=current_close, exit_reason=reason)

    if direction == -1 and current_z_score <= -target_z:
        return ExitDecision(should_exit=True, exit_price=current_close, exit_reason=reason)

    return None


# ----------------------------------------------------------------------
# 3. Master Exit Evaluator
# ----------------------------------------------------------------------

def check_trade_exit(
    direction: int,
    entry_price: float,
    current_candle: pd.Series,
    current_z_score: float,
    current_atr: float,
    bars_held: int,
    *,
    max_bars: int,
    stop_loss_atr: float = 1.5,
    target_z: float = 0.0,
    active_stop_price: Optional[float] = None,
) -> Optional[ExitDecision]:
    """
    Decides whether an open trade should exit on the current candle:
      1. Stop loss FIRST (uses the candle's open to handle gaps).
      2. Target second.
      3. Time limit third.

    max_bars has no default on purpose: the right value depends on the
    timeframe, and a wrong default would change results without any warning.
    The candle must have "open", "high", "low" and "close" (a missing one
    raises an error).
    """
    if max_bars < 1:
        raise ValueError(f"max_bars must be at least 1, got {max_bars}")

    current_open = float(current_candle["open"])
    current_high = float(current_candle["high"])
    current_low = float(current_candle["low"])
    current_close = float(current_candle["close"])

    # 1. Stop loss FIRST
    stop_exit = check_stop_loss_exit(
        direction=direction,
        entry_price=entry_price,
        current_high=current_high,
        current_low=current_low,
        current_atr=current_atr,
        stop_loss_atr=stop_loss_atr,
        stop_price=active_stop_price,
        current_open=current_open,
    )
    if stop_exit is not None:
        return stop_exit

    # 2. Profit target
    target_exit = check_target_exit(
        direction=direction,
        current_close=current_close,
        current_z_score=current_z_score,
        target_z=target_z,
    )
    if target_exit is not None:
        return target_exit

    # 3. Time limit
    if bars_held >= max_bars:
        return ExitDecision(
            should_exit=True,
            exit_price=current_close,
            exit_reason="time_limit",
        )

    return None