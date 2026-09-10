"""
Market structure analysis: classifies trend by comparing consecutive
swing highs and swing lows.

Basic trend definition used here (deliberately minimal — no break of
structure / change of character yet):
  - BULLISH: the latest confirmed swing high is higher than the
    previous one, AND the latest confirmed swing low is higher than
    the previous one (higher highs, higher lows).
  - BEARISH: the latest confirmed swing high is lower than the
    previous one, AND the latest confirmed swing low is lower than
    the previous one (lower highs, lower lows).
  - RANGING: anything else — e.g. a higher high but a lower low, or
    not enough swing points yet on both sides to compare.

Swing points are detected the same way as
liquidity/detector.py::LiquidityDetector — a candle counts as a swing
high/low if it's the highest/lowest point within `lookback` candles on
each side. That means a swing point at index i is only "confirmed"
once `lookback` candles after it exist — this is a deliberate delay,
not lookahead bias: every reading only ever compares confirmed swing
points that lie fully in the past relative to when they're confirmed,
so this is safe to use in backtesting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Sequence

from app.analysis_engine.domain.candle import Candle


class MarketStructureTrend(str, Enum):
    """Qualitative trend bucket based on swing high/low progression."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"


@dataclass(frozen=True)
class StructureReading:
    """The market structure trend as of a specific confirmed swing point."""

    timestamp: object  # matches Candle.timestamp's type
    trend: MarketStructureTrend
    last_swing_high: float | None
    last_swing_low: float | None


class StructureAnalyzer:
    """
    Tracks swing highs and swing lows over a candle series and
    classifies the market's trend as BULLISH, BEARISH, or RANGING based
    on whether swing highs/lows are progressing upward, downward, or
    mixed.

    lookback: how many candles on each side must be lower (for a high)
        or higher (for a low) for the middle candle to count as a swing
        point. Matches LiquidityDetector's definition so both modules
        agree on what counts as a swing point.
    """

    def __init__(self, lookback: int = 2) -> None:
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        self.lookback = lookback

    def analyze(self, candles: Sequence[Candle]) -> List[StructureReading]:
        """
        Full pipeline: candles -> confirmed swing highs/lows, in time
        order -> a StructureReading every time a new swing point is
        confirmed, classifying trend using only swing points confirmed
        up to that point (no lookahead).
        """
        lb = self.lookback
        n = len(candles)

        # (timestamp, price, is_high) for every confirmed swing point,
        # in the order they're confirmed (i.e. candle order). A candle
        # can in rare cases be both a swing high and a swing low (e.g.
        # very short/flat windows), so both get recorded independently,
        # same as LiquidityDetector._find_swing_points does.
        swing_points: list[tuple[object, float, bool]] = []

        for i in range(lb, n - lb):
            candle = candles[i]
            window = candles[i - lb : i + lb + 1]

            if candle.high == max(c.high for c in window):
                swing_points.append((candle.timestamp, candle.high, True))

            if candle.low == min(c.low for c in window):
                swing_points.append((candle.timestamp, candle.low, False))

        readings: List[StructureReading] = []
        last_high: float | None = None
        prev_high: float | None = None
        last_low: float | None = None
        prev_low: float | None = None

        for timestamp, price, is_high in swing_points:
            if is_high:
                prev_high = last_high
                last_high = price
            else:
                prev_low = last_low
                last_low = price

            trend = self._classify_trend(last_high, prev_high, last_low, prev_low)

            readings.append(
                StructureReading(
                    timestamp=timestamp,
                    trend=trend,
                    last_swing_high=last_high,
                    last_swing_low=last_low,
                )
            )

        return readings

    def _classify_trend(
        self,
        last_high: float | None,
        prev_high: float | None,
        last_low: float | None,
        prev_low: float | None,
    ) -> MarketStructureTrend:
        # Need at least two confirmed highs AND two confirmed lows
        # before there's anything meaningful to compare.
        if prev_high is None or prev_low is None:
            return MarketStructureTrend.RANGING

        higher_high = last_high is not None and last_high > prev_high
        higher_low = last_low is not None and last_low > prev_low
        lower_high = last_high is not None and last_high < prev_high
        lower_low = last_low is not None and last_low < prev_low

        if higher_high and higher_low:
            return MarketStructureTrend.BULLISH
        if lower_high and lower_low:
            return MarketStructureTrend.BEARISH
        return MarketStructureTrend.RANGING

    def current_trend(self, candles: Sequence[Candle]) -> MarketStructureTrend:
        """Convenience check: what's the trend right now, based on the
        most recent reading available? Defaults to RANGING if there
        isn't enough data yet to classify."""
        readings = self.analyze(candles)
        return readings[-1].trend if readings else MarketStructureTrend.RANGING