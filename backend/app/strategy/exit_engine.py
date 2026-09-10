"""
Exit level calculation, using a fixed risk:reward ratio.

Given an EntrySignal (which already carries entry_price and
stop_loss), this computes a take_profit that's `risk_reward_ratio`
times the distance being risked — e.g. a ratio of 2.0 means the
target is twice as far from entry as the stop is.

Also provides a simple per-candle check for whether either level was
hit, for use in backtesting (walking candle-by-candle to see when a
trade would have closed).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.analysis_engine.domain.candle import Candle
from app.strategy.entry_engine import EntrySignal, TradeDirection


class ExitReason(str, Enum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


@dataclass(frozen=True)
class ExitLevels:
    """The two prices that end a trade, plus the ratio used to derive
    take_profit from stop_loss."""

    stop_loss: float
    take_profit: float
    risk_reward_ratio: float


class ExitEngine:
    """
    Computes fixed risk:reward or fixed pip exit levels for a trade, and can check
    a single candle to see whether the trade would have closed on it.

    take_profit_pips: how many pips away from entry price the take_profit target sits at.
        Default is 100.0 pips.
    risk_reward_ratio: how many multiples of the risked distance (entry_price to stop_loss)
        the take_profit sits at if take_profit_pips is None.
    """

    def __init__(
        self,
        risk_reward_ratio: float = 3.0,
        take_profit_pips: float | None = None,
    ) -> None:
        if risk_reward_ratio <= 0:
            raise ValueError("risk_reward_ratio must be > 0")
        if take_profit_pips is not None and take_profit_pips <= 0:
            raise ValueError("take_profit_pips must be > 0")
        self.risk_reward_ratio = risk_reward_ratio
        self.take_profit_pips = take_profit_pips

    def compute_exit_levels(self, entry: EntrySignal, pip_size: float | None = None) -> ExitLevels:
        risk = abs(entry.entry_price - entry.stop_loss)

        if self.take_profit_pips is not None and self.take_profit_pips > 0:
            if pip_size is None:
                symbol_upper = getattr(entry, "symbol", "").upper()
                pip_size = 0.01 if "JPY" in symbol_upper else 0.0001

            tp_distance = self.take_profit_pips * pip_size
            if entry.direction == TradeDirection.BUY:
                take_profit = entry.entry_price + tp_distance
            else:
                take_profit = entry.entry_price - tp_distance

            effective_rr = round(tp_distance / max(risk, 1e-6), 2)
            return ExitLevels(
                stop_loss=entry.stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=effective_rr,
            )

        if entry.direction == TradeDirection.BUY:
            take_profit = entry.entry_price + risk * self.risk_reward_ratio
        else:
            take_profit = entry.entry_price - risk * self.risk_reward_ratio

        return ExitLevels(
            stop_loss=entry.stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=self.risk_reward_ratio,
        )

    def check_exit(
        self,
        direction: TradeDirection,
        stop_loss: float,
        take_profit: float,
        candle: Candle,
    ) -> ExitReason | None:
        """Checks a single candle's high/low against both levels.

        If a candle's range spans both the stop and the target (can
        happen on a volatile bar), this assumes the stop was hit first
        — the conservative assumption, since without tick-level data
        there's no way to know which level price actually reached
        first within that candle.
        """
        if direction == TradeDirection.BUY:
            if candle.low <= stop_loss:
                return ExitReason.STOP_LOSS
            if candle.high >= take_profit:
                return ExitReason.TAKE_PROFIT
        else:
            if candle.high >= stop_loss:
                return ExitReason.STOP_LOSS
            if candle.low <= take_profit:
                return ExitReason.TAKE_PROFIT

        return None