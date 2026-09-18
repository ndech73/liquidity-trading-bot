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


class ExitType(str, Enum):
    TP1 = "TP1"
    TP2 = "TP2"
    EARLY_BREAKEVEN = "EARLY_BREAKEVEN"
    FULL_STOP_LOSS = "FULL_STOP_LOSS"
    FRIDAY_CLOSE = "FRIDAY_CLOSE"


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
    early_breakeven_trigger_pips: profit in pips required to activate break-even protection.
    early_breakeven_buffer_pips: buffer in pips added to entry when moving stop loss to break-even.
    """

    def __init__(
        self,
        risk_reward_ratio: float = 3.0,
        take_profit_pips: float | None = None,
        early_breakeven_trigger_pips: float | None = None,
        early_breakeven_buffer_pips: float | None = None,
    ) -> None:
        if risk_reward_ratio <= 0:
            raise ValueError("risk_reward_ratio must be > 0")
        if take_profit_pips is not None and take_profit_pips <= 0:
            raise ValueError("take_profit_pips must be > 0")
        self.risk_reward_ratio = risk_reward_ratio
        self.take_profit_pips = take_profit_pips

        settings = None
        try:
            from app.core.settings import get_settings
            settings = get_settings().analysis
        except Exception:
            pass

        self.early_breakeven_trigger_pips = (
            early_breakeven_trigger_pips
            if early_breakeven_trigger_pips is not None
            else (getattr(settings, "early_breakeven_trigger_pips", 8.0) if settings else 8.0)
        )
        self.early_breakeven_buffer_pips = (
            early_breakeven_buffer_pips
            if early_breakeven_buffer_pips is not None
            else (getattr(settings, "early_breakeven_buffer_pips", 1.0) if settings else 1.0)
        )

    def compute_exit_levels(
        self,
        entry: EntrySignal,
        pip_size: float | None = None,
        custom_rr: float | None = None,
    ) -> ExitLevels:
        rr = custom_rr if custom_rr is not None else self.risk_reward_ratio
        risk = abs(entry.entry_price - entry.stop_loss)

        if self.take_profit_pips is not None and self.take_profit_pips > 0 and custom_rr is None:
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
            take_profit = entry.entry_price + risk * rr
        else:
            take_profit = entry.entry_price - risk * rr

        return ExitLevels(
            stop_loss=entry.stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=rr,
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

    def compute_breakeven_sl(
        self,
        direction: TradeDirection | str,
        entry_price: float,
        pip_size: float,
        buffer_pips: float | None = None,
    ) -> float:
        """
        Computes the break-even stop loss price with the specified buffer.
        For BUY: entry_price + (buffer_pips * pip_size)
        For SELL: entry_price - (buffer_pips * pip_size)
        """
        buf = buffer_pips if buffer_pips is not None else self.early_breakeven_buffer_pips
        dir_str = direction.value.upper() if isinstance(direction, TradeDirection) else str(direction).upper()
        if dir_str == "BUY":
            return round(entry_price + (buf * pip_size), 5)
        else:
            return round(entry_price - (buf * pip_size), 5)

    def should_trigger_breakeven(
        self,
        direction: TradeDirection | str,
        entry_price: float,
        current_price: float,
        pip_size: float,
        trigger_pips: float | None = None,
        risk_pips: float | None = None,
        rr_trigger: float = 1.0,
    ) -> bool:
        """
        Checks whether unrealized profit meets or exceeds the break-even trigger threshold.
        Supports both fixed pip trigger and dynamic risk-reward multiple trigger (e.g. 1.0 RR).
        """
        dir_str = direction.value.upper() if isinstance(direction, TradeDirection) else str(direction).upper()
        if dir_str == "BUY":
            profit_pips = (current_price - entry_price) / pip_size
        else:
            profit_pips = (entry_price - current_price) / pip_size

        base_trigger = trigger_pips if trigger_pips is not None else self.early_breakeven_trigger_pips
        if risk_pips is not None and risk_pips > 0:
            effective_trigger = min(base_trigger, max(2.0, risk_pips * rr_trigger))
        else:
            effective_trigger = base_trigger

        return profit_pips >= effective_trigger - 1e-9

    def determine_exit_type(
        self,
        direction: TradeDirection | str,
        entry_price: float,
        exit_price: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        is_breakeven: bool = False,
        is_friday_close: bool = False,
        tp_label: str | None = None,
        pip_size: float = 0.0001,
    ) -> ExitType:
        """
        Determines whether an exit corresponds to TP1, TP2, EARLY_BREAKEVEN, FULL_STOP_LOSS, or FRIDAY_CLOSE.
        """
        if is_friday_close:
            return ExitType.FRIDAY_CLOSE

        dir_str = direction.value.upper() if isinstance(direction, TradeDirection) else str(direction).upper()
        is_buy = dir_str == "BUY"
        profit_pips = ((exit_price - entry_price) / pip_size) if is_buy else ((entry_price - exit_price) / pip_size)

        # 1. Take Profit hit
        if take_profit is not None:
            tp_reached = (exit_price >= take_profit - (pip_size * 0.5)) if is_buy else (exit_price <= take_profit + (pip_size * 0.5))
            if tp_reached:
                if tp_label and str(tp_label).upper() in ("TP2", "2"):
                    return ExitType.TP2
                return ExitType.TP1

        if tp_label and str(tp_label).upper() in ("TP1", "TP2") and profit_pips > 0:
            if not (is_breakeven and abs(profit_pips - self.early_breakeven_buffer_pips) < 2.0):
                return ExitType.TP2 if str(tp_label).upper() == "TP2" else ExitType.TP1

        # 2. Break-Even hit
        sl_is_be = False
        if stop_loss is not None:
            if is_buy and stop_loss >= entry_price - 1e-9:
                sl_is_be = True
            elif not is_buy and stop_loss <= entry_price + 1e-9:
                sl_is_be = True

        if is_breakeven or sl_is_be:
            if profit_pips >= -1.0:
                return ExitType.EARLY_BREAKEVEN

        # 3. If in clear profit but TP level was not explicitly set
        if profit_pips > 0 and not is_breakeven:
            return ExitType.TP2 if tp_label and str(tp_label).upper() in ("TP2", "2") else ExitType.TP1

        # 4. Full Stop Loss
        return ExitType.FULL_STOP_LOSS