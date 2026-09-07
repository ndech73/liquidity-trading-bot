"""
Expansion detection: identifies periods where price range is growing
well beyond recent baseline — the "release" phase that follows a
liquidity sweep and rejection, per the Liquidity Event Sequence
(COMPRESSION -> ... -> LIQUIDITY SWEEP -> REJECTION -> EXPANSION).

This is the mirror case of CompressionDetector: instead of checking
whether range has contracted, it checks whether range has grown past
baseline — plus which direction that expansion is moving, since a big
range alone doesn't tell you if it's a real directional move or just
noisy chop.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import mean
from typing import List, Sequence

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.volatility.analyzer import VolatilityAnalyzer


class ExpansionDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class ExpansionReading:
    """Expansion state for a single point in time."""

    timestamp: object  # matches Candle.timestamp's type
    recent_avg_range: float
    baseline_avg_range: float
    expansion_ratio: float  # recent_avg_range / baseline_avg_range
    is_expanding: bool
    direction: ExpansionDirection


class ExpansionDetector:
    """
    Compares a short recent window of true-range values against a
    longer baseline window. If the recent window's average range is
    meaningfully larger than the baseline, the market is "expanding"
    — releasing, likely mid-way through a directional move.

    recent_window: how many of the latest candles count as "right now".
    baseline_window: how many candles (immediately preceding the
        recent window) define "normal" range for comparison.
    expansion_threshold: recent_avg_range must be >= this multiple of
        baseline_avg_range to count as expanding (e.g. 1.5 means range
        must have grown to 150% or more of baseline).
    direction_threshold: net price movement over the recent window
        must be at least this fraction of the recent window's total
        range to count as a clear direction, rather than NEUTRAL
        (choppy back-and-forth that nets out near zero).
    """

    def __init__(
        self,
        recent_window: int = 5,
        baseline_window: int = 20,
        expansion_threshold: float = 1.5,
        direction_threshold: float = 0.3,
    ) -> None:
        if recent_window < 1:
            raise ValueError("recent_window must be >= 1")
        if baseline_window < 1:
            raise ValueError("baseline_window must be >= 1")
        if expansion_threshold <= 1:
            raise ValueError("expansion_threshold must be greater than 1")
        if not (0 < direction_threshold <= 1):
            raise ValueError("direction_threshold must be between 0 and 1")

        self.recent_window = recent_window
        self.baseline_window = baseline_window
        self.expansion_threshold = expansion_threshold
        self.direction_threshold = direction_threshold
        self._volatility_analyzer = VolatilityAnalyzer()

    def analyze(self, candles: Sequence[Candle]) -> List[ExpansionReading]:
        """
        Full pipeline: candles -> true ranges -> an ExpansionReading for
        every point where both a recent window and a preceding baseline
        window are available.
        """
        true_ranges = self._volatility_analyzer.compute_true_range(candles)
        min_required = self.recent_window + self.baseline_window
        if len(true_ranges) < min_required:
            return []

        readings: List[ExpansionReading] = []

        for i in range(min_required - 1, len(true_ranges)):
            recent_slice = true_ranges[i - self.recent_window + 1 : i + 1]
            baseline_slice = true_ranges[
                i - min_required + 1 : i - self.recent_window + 1
            ]

            recent_avg = mean(recent_slice)
            baseline_avg = mean(baseline_slice)

            ratio = recent_avg / baseline_avg if baseline_avg else 0.0
            is_expanding = ratio >= self.expansion_threshold

            # candles corresponding to this recent window: TR[i] maps to
            # candles[i + 1], same offset used throughout this codebase.
            recent_candles = candles[
                i - self.recent_window + 2 : i + 2
            ]
            direction = self._classify_direction(recent_candles, recent_avg)

            readings.append(
                ExpansionReading(
                    timestamp=candles[i + 1].timestamp,
                    recent_avg_range=recent_avg,
                    baseline_avg_range=baseline_avg,
                    expansion_ratio=ratio,
                    is_expanding=is_expanding,
                    direction=direction,
                )
            )

        return readings

    def is_currently_expanding(self, candles: Sequence[Candle]) -> bool:
        """Convenience check: is the market expanding right now, based
        on the most recent reading available?"""
        readings = self.analyze(candles)
        return readings[-1].is_expanding if readings else False

    def _classify_direction(
        self, recent_candles: Sequence[Candle], recent_avg_range: float
    ) -> ExpansionDirection:
        if not recent_candles or recent_avg_range == 0:
            return ExpansionDirection.NEUTRAL

        net_move = recent_candles[-1].close - recent_candles[0].open
        # Normalize against total range covered, not just avg range, so
        # this scales sensibly regardless of window size.
        total_range = recent_avg_range * len(recent_candles)
        if total_range == 0:
            return ExpansionDirection.NEUTRAL

        net_ratio = net_move / total_range

        if net_ratio >= self.direction_threshold:
            return ExpansionDirection.BULLISH
        if net_ratio <= -self.direction_threshold:
            return ExpansionDirection.BEARISH
        return ExpansionDirection.NEUTRAL