from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ExitDecision:
    should_exit: bool
    exit_price: float
    exit_reason: str  # "target_equilibrium", "stop_loss", "time_limit"


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
    high = float(current_candle["high"])
    low = float(current_candle["low"])
    close = float(current_candle["close"])

    # 1. Target Exit: Rubber band fully relaxed (z reaches 0)
    if direction == 1 and current_z_score >= 0.0:
        return ExitDecision(
            should_exit=True,
            exit_price=close,
            exit_reason="target_equilibrium",
        )
    elif direction == -1 and current_z_score <= 0.0:
        return ExitDecision(
            should_exit=True,
            exit_price=close,
            exit_reason="target_equilibrium",
        )

    # 2. Stop Loss: Price broke beyond statistical safety boundary
    max_loss_distance = stop_loss_atr * current_atr
    if direction == 1:
        stop_price = entry_price - max_loss_distance
        if low <= stop_price:
            return ExitDecision(
                should_exit=True,
                exit_price=stop_price,
                exit_reason="stop_loss",
            )
    elif direction == -1:
        stop_price = entry_price + max_loss_distance
        if high >= stop_price:
            return ExitDecision(
                should_exit=True,
                exit_price=stop_price,
                exit_reason="stop_loss",
            )

    # 3. Time Limit: Trade reached maximum holding duration
    if bars_held >= max_bars:
        return ExitDecision(
            should_exit=True,
            exit_price=close,
            exit_reason="time_limit",
        )

    return None