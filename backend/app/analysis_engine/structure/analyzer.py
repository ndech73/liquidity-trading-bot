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


class StructureRegime(str, Enum):
    """Market structure regime: TRENDING vs RANGING."""

    TRENDING = "TRENDING"
    RANGING = "RANGING"


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
    structure_lookback_swings: how many swing points to inspect when classifying
        whether structure is TRENDING or RANGING (default 6).
    """

    def __init__(
        self,
        lookback: int = 2,
        structure_lookback_swings: int | None = None,
    ) -> None:
        if lookback < 1:
            raise ValueError("lookback must be >= 1")
        self.lookback = lookback

        settings = None
        try:
            from app.core.settings import get_settings
            settings = get_settings().analysis
        except Exception:
            pass

        self.structure_lookback_swings = (
            structure_lookback_swings
            if structure_lookback_swings is not None
            else (getattr(settings, "structure_lookback_swings", 6) if settings else 6)
        )

    def find_swing_points(self, candles: Sequence[Candle]) -> list[tuple[object, float, bool]]:
        """
        Extracts confirmed swing points from candles as (timestamp, price, is_high) tuples.
        """
        lb = self.lookback
        n = len(candles)
        swing_points: list[tuple[object, float, bool]] = []
        for i in range(lb, n - lb):
            candle = candles[i]
            window = candles[i - lb : i + lb + 1]

            if candle.high == max(c.high for c in window):
                swing_points.append((candle.timestamp, candle.high, True))

            if candle.low == min(c.low for c in window):
                swing_points.append((candle.timestamp, candle.low, False))
        return swing_points

    def analyze(self, candles: Sequence[Candle]) -> List[StructureReading]:
        """
        Full pipeline: candles -> confirmed swing highs/lows, in time
        order -> a StructureReading every time a new swing point is
        confirmed, classifying trend using only swing points confirmed
        up to that point (no lookahead).
        """
        swing_points = self.find_swing_points(candles)

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

    def classify_regime_from_swings(
        self,
        swings: Sequence[Any],
        lookback_swings: int | None = None,
    ) -> StructureRegime:
        """
        Classifies whether the market is TRENDING or RANGING based on the last N
        (default structure_lookback_swings, e.g. 6) swing points.

        A structure is TRENDING if:
          - Bullish: swing highs are strictly ascending (HH) AND swing lows are strictly ascending (HL),
            representing consecutive Break of Structure (BOS) continuing upward without Change of Character (CHoCH).
          - Bearish: swing highs are strictly descending (LH) AND swing lows are strictly descending (LL),
            representing consecutive Break of Structure (BOS) continuing downward without Change of Character (CHoCH).
        Otherwise, the structure is classified as RANGING.
        """
        n_swings = lookback_swings if lookback_swings is not None else self.structure_lookback_swings
        if not swings or len(swings) < 4:
            return StructureRegime.RANGING

        recent = swings[-n_swings:]

        parsed: list[tuple[float, bool]] = []
        for s in recent:
            if isinstance(s, tuple):
                if len(s) >= 3:
                    parsed.append((float(s[1]), bool(s[2])))
                elif len(s) == 2:
                    parsed.append((float(s[0]), bool(s[1])))
            elif isinstance(s, dict):
                p = float(s["price"])
                h = bool(s.get("is_high", s.get("is_swing_high", False)))
                parsed.append((p, h))
            elif hasattr(s, "price") and hasattr(s, "is_high"):
                parsed.append((float(s.price), bool(s.is_high)))
            else:
                continue

        highs = [p for p, is_high in parsed if is_high]
        lows = [p for p, is_high in parsed if not is_high]

        # Need at least 2 highs and 2 lows to establish a sequence of HH+HL or LH+LL
        if len(highs) < 2 or len(lows) < 2:
            return StructureRegime.RANGING

        is_bullish = (
            all(highs[i] < highs[i + 1] for i in range(len(highs) - 1))
            and all(lows[i] < lows[i + 1] for i in range(len(lows) - 1))
        )
        if is_bullish:
            return StructureRegime.TRENDING

        is_bearish = (
            all(highs[i] > highs[i + 1] for i in range(len(highs) - 1))
            and all(lows[i] > lows[i + 1] for i in range(len(lows) - 1))
        )
        if is_bearish:
            return StructureRegime.TRENDING

        return StructureRegime.RANGING

    def classify_regime(
        self,
        candles: Sequence[Candle],
        lookback_swings: int | None = None,
    ) -> StructureRegime:
        """
        Extracts confirmed swing points from candles and classifies the market structure
        regime as TRENDING or RANGING.
        """
        swings = self.find_swing_points(candles)
        return self.classify_regime_from_swings(swings, lookback_swings=lookback_swings)

    def is_trending(
        self,
        candles: Sequence[Candle],
        lookback_swings: int | None = None,
    ) -> bool:
        """
        Convenience check: returns True if structure is currently TRENDING.
        """
        return self.classify_regime(candles, lookback_swings=lookback_swings) == StructureRegime.TRENDING


# Alias for compatibility
MarketStructureAnalyzer = StructureAnalyzer