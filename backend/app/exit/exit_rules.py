"""
exit_rules.py
-------------
Dynamic mathematical exit rules on H1 and H4:
  1. Target Exit (Equilibrium)   : z-score reaches 0 (rubber band has fully relaxed to the mean).
  2. Safety Stop Loss (1.5x ATR) : Price breaches statistical boundary, cutting losses early.
  3. Time Limit Guard (Diffusion): Exits after max_bars if price is wandering without momentum.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    exit_price: float
    exit_reason: str  # "target_equilibrium", "stop_loss", "time_limit"


# ----------------------------------------------------------------------
# 1. Target Exit: Price snapped back to fair value (z reaches 0)
# ----------------------------------------------------------------------

def check_target_exit(
    direction: int,
    current_close: float,
    current_z_score: float,
) -> Optional[ExitDecision]:
    """
    Takes profit as soon as price returns to the 24-hour moving average:
      - Long  (+1) : exit when z >= 0
      - Short (-1) : exit when z <= 0
    """
    if direction == 1 and current_z_score >= 0.0:
        return ExitDecision(
            should_exit=True,
            exit_price=current_close,
            exit_reason="target_equilibrium",
        )
    elif direction == -1 and current_z_score <= 0.0:
        return ExitDecision(
            should_exit=True,
            exit_price=current_close,
            exit_reason="target_equilibrium",
        )

    return None


# ----------------------------------------------------------------------
# 2. Stop Loss Exit: Price broke beyond statistical boundary (1.5x ATR)
# ----------------------------------------------------------------------

def check_stop_loss_exit(
    direction: int,
    entry_price: float,
    current_high: float,
    current_low: float,
    current_atr: float,
    stop_loss_atr: float = 1.5,
) -> Optional[ExitDecision]:
    """
    Emergency exit if price moves 1.5x ATR against the trade.
    """
    max_loss_distance = stop_loss_atr * current_atr

    # For Long trade (+1): stop sits below entry
    if direction == 1:
        stop_price = entry_price - max_loss_distance
        if current_low <= stop_price:
            return ExitDecision(
                should_exit=True,
                exit_price=stop_price,
                exit_reason="stop_loss",
            )

    # For Short trade (-1): stop sits above entry
    elif direction == -1:
        stop_price = entry_price + max_loss_distance
        if current_high >= stop_price:
            return ExitDecision(
                should_exit=True,
                exit_price=stop_price,
                exit_reason="stop_loss",
            )

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
    stop_loss_atr: float = 1.5,
    max_bars: int = 16,
) -> Optional[ExitDecision]:
    """
    Evaluates whether an active trade should exit on the current candle:
      1. Profit Target Check (Equilibrium z = 0)
      2. Safety Stop Loss Check (1.5x ATR breach)
      3. Time Limit Diffusion Check (max_bars reached)
    """
    current_high = float(current_candle["high"])
    current_low = float(current_candle["low"])
    current_close = float(current_candle["close"])

    # 1. Check profit target
    target_exit = check_target_exit(direction, current_close, current_z_score)
    if target_exit is not None:
        return target_exit

    # 2. Check safety stop loss
    stop_exit = check_stop_loss_exit(
        direction, entry_price, current_high, current_low, current_atr, stop_loss_atr
    )
    if stop_exit is not None:
        return stop_exit

    # 3. Check time limit
    if bars_held >= max_bars:
        return ExitDecision(
            should_exit=True,
            exit_price=current_close,
            exit_reason="time_limit",
        )

    return None