"""
Entry signal generation.

Strategy in plain terms: a liquidity zone (an old swing high/low where
stop orders are likely resting) gets swept — price pokes through it —
and then rejects back the other way. That's the "stop hunt" pattern:
big players run the resting stops, then the real move goes the
opposite direction. This module turns that pattern into a concrete
trade signal.

Direction logic:
  - A BUYSIDE zone (a swing HIGH, where buy-stops rest above price)
    gets swept upward, then price rejects back down -> that's a SELL
    signal (bearish reversal).
  - A SELLSIDE zone (a swing LOW, where sell-stops rest below price)
    gets swept downward, then price rejects back up -> that's a BUY
    signal (bullish reversal).

A signal is only produced when ALL of these are true (hard filters):
  1. A sweep happened (from snapshot.sweep_events).
  2. Price rejected back through the swept level within
     `rejection_confirmation_candles` candles of the sweep.
  3. The broader trend (from StructureAnalyzer) doesn't clearly
     contradict the signal direction — e.g. a SELL signal is blocked
     if the market is in a confirmed BULLISH structure.
  4. The market is currently expanding (ExpansionDetector), in the
     same direction as the signal — confirms the reversal has real
     follow-through instead of being a weak, fading move.

Compression is checked too, but only as a SOFT signal: it's recorded
on the EntrySignal for extra context/confidence, but a signal is never
blocked just because the market wasn't compressed beforehand. Reasoning:
requiring compression before every single sweep would filter out a lot
of otherwise valid setups — sweeps happen without a prior squeeze too.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Sequence

from app.analysis_engine.domain.candle import Candle, Timeframe
from app.analysis_engine.domain.liquidity import LiquiditySide, LiquidityType
from app.analysis_engine.engine import MarketSnapshot
from app.analysis_engine.structure.analyzer import MarketStructureTrend, StructureAnalyzer
from app.analysis_engine.volatility.expansion import ExpansionDirection


class TradeDirection(str, Enum):
    """Which way the resulting trade would go. Deliberately separate
    from LiquiditySide (BUYSIDE/SELLSIDE), which describes the zone
    that got swept, not the trade direction — sweeping a BUYSIDE zone
    actually produces a SELL trade, not a BUY, so conflating the two
    would be confusing."""

    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class EntrySignal:
    """A single actionable entry opportunity."""

    symbol: str
    timeframe: Timeframe
    direction: TradeDirection
    signal_time: datetime  # timestamp of the candle that confirmed rejection
    entry_price: float  # close of the confirmation candle
    stop_loss: float  # placed beyond the sweep's extreme price, with a buffer
    zone_id: str
    liquidity_type: LiquidityType
    level_price: float  # the swept zone's price level
    sweep_price: float  # how far price ran during the sweep
    trend: MarketStructureTrend
    expansion_confirmed: bool
    compression_confirmed: bool  # soft signal only — never gates the trade


class EntryEngine:
    """
    Scans a MarketSnapshot for sweep events and turns qualifying ones
    into EntrySignals.

    rejection_confirmation_candles: how many candles after the sweep
        to look for a close back through the level before giving up on
        that sweep as a valid setup.
    stop_buffer_pct: extra room placed beyond the sweep's extreme price
        for the stop loss, as a fraction of price (e.g. 0.0005 = 0.05%),
        so the stop isn't sitting exactly on a level that's likely to
        get re-tested.
    allow_ranging_trend: if True, RANGING structure doesn't block a
        signal in either direction (only a clearly opposing trend
        does). If False, only a matching trend (BULLISH for BUY,
        BEARISH for SELL) is allowed through.
    """

    def __init__(
        self,
        structure_analyzer: StructureAnalyzer | None = None,
        rejection_confirmation_candles: int = 3,
        stop_buffer_pct: float = 0.0005,
        allow_ranging_trend: bool = True,
        require_expansion: bool = True,
    ) -> None:
        if rejection_confirmation_candles < 0:
            raise ValueError("rejection_confirmation_candles must be >= 0")
        if stop_buffer_pct < 0:
            raise ValueError("stop_buffer_pct must be >= 0")

        self.structure_analyzer = structure_analyzer or StructureAnalyzer()
        self.rejection_confirmation_candles = rejection_confirmation_candles
        self.stop_buffer_pct = stop_buffer_pct
        self.allow_ranging_trend = allow_ranging_trend
        self.require_expansion = require_expansion

    def evaluate(
        self, snapshot: MarketSnapshot, candles: Sequence[Candle]
    ) -> list[EntrySignal]:
        """Checks every sweep event in `snapshot` and returns an
        EntrySignal for each one that passes all hard filters."""
        if not candles:
            return []

        trend = self.structure_analyzer.current_trend(candles)
        signals: list[EntrySignal] = []

        for event in snapshot.sweep_events:
            direction = self._implied_direction(event.side)

            if not self._trend_allows(direction, trend):
                continue

            confirmation_candle = self._find_rejection_candle(
                event.occurred_at, event.level_price, direction, candles
            )
            if confirmation_candle is None:
                continue

            expansion_confirmed = self._expansion_confirms(direction, snapshot)
            if self.require_expansion and not expansion_confirmed:
                continue

            compression_confirmed = bool(
                snapshot.compression is not None and snapshot.compression.is_compressed
            )

            stop_loss = self._compute_stop_loss(direction, event.sweep_price)

            signals.append(
                EntrySignal(
                    symbol=event.symbol,
                    timeframe=event.timeframe,
                    direction=direction,
                    signal_time=confirmation_candle.timestamp,
                    entry_price=confirmation_candle.close,
                    stop_loss=stop_loss,
                    zone_id=event.zone_id,
                    liquidity_type=event.liquidity_type,
                    level_price=event.level_price,
                    sweep_price=event.sweep_price,
                    trend=trend,
                    expansion_confirmed=expansion_confirmed,
                    compression_confirmed=compression_confirmed,
                )
            )

        return signals

    def _implied_direction(self, swept_side: LiquiditySide) -> TradeDirection:
        # Sweeping a BUYSIDE (high) zone implies a SELL reversal;
        # sweeping a SELLSIDE (low) zone implies a BUY reversal.
        return (
            TradeDirection.SELL
            if swept_side == LiquiditySide.BUYSIDE
            else TradeDirection.BUY
        )

    def _trend_allows(self, direction: TradeDirection, trend: MarketStructureTrend) -> bool:
        if trend == MarketStructureTrend.RANGING:
            return self.allow_ranging_trend

        if direction == TradeDirection.BUY:
            return trend == MarketStructureTrend.BULLISH
        return trend == MarketStructureTrend.BEARISH

    def _find_rejection_candle(
        self,
        swept_at: datetime,
        level_price: float,
        direction: TradeDirection,
        candles: Sequence[Candle],
    ) -> Candle | None:
        """Looks for the sweep candle itself, then up to
        `rejection_confirmation_candles` candles after it, for the
        first candle whose close is back through `level_price` in the
        expected reversal direction."""
        start_index = None
        for i, candle in enumerate(candles):
            if candle.timestamp == swept_at:
                start_index = i
                break
            # detected_via can be TICK, whose occurred_at may not match
            # any candle's timestamp exactly — fall back to the last
            # candle at or before the sweep time.
            if candle.timestamp <= swept_at:
                start_index = i

        if start_index is None:
            return None

        end_index = min(start_index + self.rejection_confirmation_candles, len(candles) - 1)

        for i in range(start_index, end_index + 1):
            candle = candles[i]
            if direction == TradeDirection.BUY and candle.close > level_price:
                return candle
            if direction == TradeDirection.SELL and candle.close < level_price:
                return candle

        return None

    def _expansion_confirms(self, direction: TradeDirection, snapshot: MarketSnapshot) -> bool:
        if snapshot.expansion is None or not snapshot.expansion.is_expanding:
            return False

        if direction == TradeDirection.BUY:
            return snapshot.expansion.direction == ExpansionDirection.BULLISH
        return snapshot.expansion.direction == ExpansionDirection.BEARISH

    def _compute_stop_loss(self, direction: TradeDirection, sweep_price: float) -> float:
        if direction == TradeDirection.BUY:
            # sweep ran price down through a low; stop goes further
            # below that extreme, not right at it.
            return sweep_price * (1 - self.stop_buffer_pct)
        # sweep ran price up through a high; stop goes further above.
        return sweep_price * (1 + self.stop_buffer_pct)