"""
Volatility analysis: True Range, ATR, and market volatility regime classification.

Given a sequence of candles, this module answers:
1. How much is price moving right now? (ATR)
2. Is that movement high, low, or normal relative to recent history? (regime)

Downstream consumers (entry/exit sizing, risk engine) use the regime to
adapt behavior instead of treating every market condition the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import mean, pstdev
from typing import List, Sequence

from app.analysis_engine.domain.candle import Candle


class VolatilityRegime(str, Enum):
    """Qualitative bucket for how volatile the market currently is."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True)
class VolatilityReading:
    """The volatility state for a single point in time."""

    timestamp: object  # matches Candle.timestamp's type, whatever that is
    true_range: float
    atr: float
    regime: VolatilityRegime


class VolatilityAnalyzer:
    """
    Computes True Range and ATR over a candle series, then classifies
    each ATR value into a volatility regime relative to its own recent
    history (a rolling mean/std of ATR, not a fixed hardcoded threshold —
    this keeps it self-calibrating per instrument/timeframe).
    """

    # Floating-point tolerance for threshold comparisons. z_score is
    # derived from a subtraction/division chain (current - mean) / stdev,
    # so a z_score that is mathematically exactly equal to a threshold
    # (e.g. 1.0) can land a few ULPs below it (e.g. 0.9999999999999998)
    # purely from rounding. Without this epsilon, values sitting right on
    # a boundary get silently classified one regime lower than intended.
    _EPSILON = 1e-9

    def __init__(
        self,
        atr_period: int = 14,
        regime_lookback: int = 100,
        high_threshold_stdev: float = 1.0,
        extreme_threshold_stdev: float = 2.0,
        low_threshold_stdev: float = -1.0,
    ) -> None:
        """
        atr_period: number of periods used in Wilder's ATR smoothing.
        regime_lookback: how many recent ATR values define "normal" for
            this market (rolling mean/stdev baseline).
        *_threshold_stdev: how many standard deviations above/below the
            rolling ATR mean define HIGH/EXTREME/LOW regimes.
        """
        if atr_period < 1:
            raise ValueError("atr_period must be >= 1")
        if regime_lookback < 2:
            raise ValueError("regime_lookback must be >= 2 to compute stdev")

        self.atr_period = atr_period
        self.regime_lookback = regime_lookback
        self.high_threshold_stdev = high_threshold_stdev
        self.extreme_threshold_stdev = extreme_threshold_stdev
        self.low_threshold_stdev = low_threshold_stdev

    def compute_true_range(self, candles: Sequence[Candle]) -> List[float]:
        """
        True Range for each candle after the first:
            max(high - low, |high - prev_close|, |low - prev_close|)

        The first candle has no previous close, so it's skipped — the
        returned list is one shorter than the input.
        """
        if len(candles) < 2:
            return []

        true_ranges: List[float] = []
        for prev, curr in zip(candles, candles[1:]):
            high_low = curr.high - curr.low
            high_prev_close = abs(curr.high - prev.close)
            low_prev_close = abs(curr.low - prev.close)
            true_ranges.append(max(high_low, high_prev_close, low_prev_close))

        return true_ranges

    def compute_atr(self, candles: Sequence[Candle]) -> List[float]:
        """
        Wilder's smoothed ATR:
            first ATR = simple average of the first `atr_period` true ranges
            each ATR after = (prev_atr * (period - 1) + current_tr) / period

        Returns one ATR value per true range available after the seed
        window, so the output is shorter than the candle list by
        `atr_period` (plus 1, for the TR calculation itself).
        """
        true_ranges = self.compute_true_range(candles)
        if len(true_ranges) < self.atr_period:
            return []

        atr_values: List[float] = []
        seed = mean(true_ranges[: self.atr_period])
        atr_values.append(seed)

        for tr in true_ranges[self.atr_period :]:
            prev_atr = atr_values[-1]
            next_atr = (prev_atr * (self.atr_period - 1) + tr) / self.atr_period
            atr_values.append(next_atr)

        return atr_values

    def classify_regime(self, atr_values: Sequence[float]) -> VolatilityRegime:
        """
        Classifies the LATEST atr value relative to the rolling mean/stdev
        of the values preceding it (up to `regime_lookback` of them).

        If there isn't enough history yet to form a baseline, defaults to
        NORMAL rather than guessing.
        """
        if len(atr_values) < 2:
            return VolatilityRegime.NORMAL

        current = atr_values[-1]
        baseline_window = atr_values[-(self.regime_lookback + 1) : -1]

        if len(baseline_window) < 2:
            return VolatilityRegime.NORMAL

        baseline_mean = mean(baseline_window)
        baseline_stdev = pstdev(baseline_window)

        if baseline_stdev == 0:
            return VolatilityRegime.NORMAL

        z_score = (current - baseline_mean) / baseline_stdev

        # Epsilon-tolerant comparisons: a z_score that should mathematically
        # equal a threshold can land a hair below it due to float rounding
        # in the mean/stdev/division chain above.
        if z_score >= self.extreme_threshold_stdev - self._EPSILON:
            return VolatilityRegime.EXTREME
        if z_score >= self.high_threshold_stdev - self._EPSILON:
            return VolatilityRegime.HIGH
        if z_score <= self.low_threshold_stdev + self._EPSILON:
            return VolatilityRegime.LOW
        return VolatilityRegime.NORMAL

    def analyze(self, candles: Sequence[Candle], latest_only: bool = False) -> List[VolatilityReading]:
        """
        Full pipeline: candles -> true ranges -> ATR series -> a
        VolatilityReading (with regime) for each ATR point.

        Each reading's regime is classified using only ATR history up to
        and including that point — never future data — so this is safe
        to use in backtesting without lookahead bias.
        """
        true_ranges = self.compute_true_range(candles)
        atr_values = self.compute_atr(candles)

        if not atr_values:
            return []

        offset = self.atr_period + 1
        readings: List[VolatilityReading] = []

        if latest_only:
            i = len(atr_values) - 1
            candle_index = offset + i - 1
            tr_index = self.atr_period + i - 1
            readings.append(
                VolatilityReading(
                    timestamp=candles[candle_index].timestamp,
                    true_range=true_ranges[tr_index],
                    atr=atr_values[-1],
                    regime=self.classify_regime(atr_values),
                )
            )
            return readings

        for i, atr in enumerate(atr_values):
            candle_index = offset + i - 1
            tr_index = self.atr_period + i - 1
            readings.append(
                VolatilityReading(
                    timestamp=candles[candle_index].timestamp,
                    true_range=true_ranges[tr_index],
                    atr=atr,
                    regime=self.classify_regime(atr_values[: i + 1]),
                )
            )

        return readings