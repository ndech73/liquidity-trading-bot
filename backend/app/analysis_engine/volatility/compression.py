"""
Compression detection: identifies periods where price range is
contracting relative to recent history — the "coiling" phase that
often precedes a liquidity sweep and expansion, per the Liquidity
Event Sequence (COMPRESSION -> NEARBY LIQUIDITY -> LIQUIDITY SWEEP ->
REJECTION -> EXPANSION).

This complements VolatilityAnalyzer's regime classification: regime
looks at absolute ATR level, this looks specifically at *contraction*
trend over a short recent window — a market can be in a NORMAL regime
while still visibly compressing right before a breakout.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import List, Sequence

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.volatility.analyzer import VolatilityAnalyzer
from app.core.settings import get_settings


@dataclass(frozen=True)
class CompressionReading:
    """Compression state for a single point in time."""

    timestamp: object  # matches Candle.timestamp's type
    recent_avg_range: float
    baseline_avg_range: float
    contraction_ratio: float  # recent_avg_range / baseline_avg_range
    is_compressed: bool


class CompressionDetector:
    """
    Compares a short recent window of true-range values against a
    longer baseline window. If the recent window's average range is
    meaningfully smaller than the baseline, the market is "compressed"
    — coiling, likely to expand soon.

    recent_window: how many of the latest candles count as "right now".
    baseline_window: how many candles (immediately preceding the
        recent window) define "normal" range for comparison.
    contraction_threshold: recent_avg_range must be <= this fraction
        of baseline_avg_range to count as compressed (e.g. 0.6 means
        range must have shrunk to 60% or less of baseline).

    recent_window and baseline_window default to core/settings.py's
    AnalysisEngineSettings when left as None, so they're configurable
    via env vars instead of hardcoded. contraction_threshold has no
    corresponding setting yet, so it keeps its literal default — pass
    it explicitly if you want it configurable too.
    """

    def __init__(
        self,
        recent_window: int | None = None,
        baseline_window: int | None = None,
        contraction_threshold: float = 0.6,
    ) -> None:
        settings = get_settings().analysis
        recent_window = (
            recent_window if recent_window is not None else settings.compression_recent_window
        )
        baseline_window = (
            baseline_window
            if baseline_window is not None
            else settings.compression_baseline_window
        )

        if recent_window < 1:
            raise ValueError("recent_window must be >= 1")
        if baseline_window < 1:
            raise ValueError("baseline_window must be >= 1")
        if not (0 < contraction_threshold < 1):
            raise ValueError("contraction_threshold must be between 0 and 1")

        self.recent_window = recent_window
        self.baseline_window = baseline_window
        self.contraction_threshold = contraction_threshold
        self._volatility_analyzer = VolatilityAnalyzer()

    def analyze(self, candles: Sequence[Candle]) -> List[CompressionReading]:
        """
        Full pipeline: candles -> true ranges -> a CompressionReading for
        every point where both a recent window and a preceding baseline
        window are available.
        """
        true_ranges = self._volatility_analyzer.compute_true_range(candles)
        min_required = self.recent_window + self.baseline_window
        if len(true_ranges) < min_required:
            return []

        readings: List[CompressionReading] = []

        for i in range(min_required - 1, len(true_ranges)):
            recent_slice = true_ranges[i - self.recent_window + 1 : i + 1]
            baseline_slice = true_ranges[
                i - min_required + 1 : i - self.recent_window + 1
            ]

            recent_avg = mean(recent_slice)
            baseline_avg = mean(baseline_slice)

            ratio = recent_avg / baseline_avg if baseline_avg else 0.0
            is_compressed = ratio <= self.contraction_threshold

            readings.append(
                CompressionReading(
                    timestamp=candles[i + 1].timestamp,
                    recent_avg_range=recent_avg,
                    baseline_avg_range=baseline_avg,
                    contraction_ratio=ratio,
                    is_compressed=is_compressed,
                )
            )

        return readings

    def is_currently_compressed(self, candles: Sequence[Candle]) -> bool:
        """Convenience check: is the market compressed right now, based
        on the most recent reading available?"""
        readings = self.analyze(candles)
        return readings[-1].is_compressed if readings else False