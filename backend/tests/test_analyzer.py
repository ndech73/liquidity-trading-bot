"""Tests for app.analysis_engine.volatility.analyzer."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from app.analysis_engine.domain.candle import Candle, Timeframe
from app.analysis_engine.volatility.analyzer import (
    VolatilityAnalyzer,
    VolatilityRegime,
    VolatilityReading,
)

START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def doji_candle(index: int, base: float, high_offset: float) -> Candle:
    """A candle whose open/close/low all sit at `base`, with only the
    high raised by `high_offset`. Because open == close == low for
    every candle in a series built this way, and price never actually
    moves between candles, True Range for candle i collapses to exactly
    `high_offset` — which lets tests assert exact expected numbers
    instead of just 'a number came out'."""
    return Candle(
        symbol="EURUSD",
        timeframe=Timeframe.M1,
        timestamp=START + timedelta(minutes=index),
        open=base,
        high=base + high_offset,
        low=base,
        close=base,
    )


def varied_series(n: int, base: float = 1.1000) -> list[Candle]:
    """A longer deterministic series with a repeating offset pattern,
    used for pipeline-shape tests where exact numbers don't matter."""
    offsets = [0.0010 * (1 + (i % 7)) for i in range(n)]
    return [doji_candle(i, base, off) for i, off in enumerate(offsets)]


class TestComputeTrueRange:
    def test_empty_and_single_candle_return_empty(self) -> None:
        analyzer = VolatilityAnalyzer()
        assert analyzer.compute_true_range([]) == []
        assert analyzer.compute_true_range([doji_candle(0, 1.1000, 0.005)]) == []

    def test_matches_hand_calculated_values(self) -> None:
        offsets = [0.005, 0.008, 0.009, 0.010, 0.007]
        candles = [doji_candle(i, 1.1000, off) for i, off in enumerate(offsets)]
        analyzer = VolatilityAnalyzer()

        true_ranges = analyzer.compute_true_range(candles)

        # TR for candles 1..4, since candle 0 has no previous close
        assert true_ranges == pytest.approx([0.008, 0.009, 0.010, 0.007])


class TestComputeATR:
    def test_fewer_true_ranges_than_period_returns_empty(self) -> None:
        analyzer = VolatilityAnalyzer(atr_period=5, regime_lookback=2)
        candles = varied_series(4)  # only 3 true ranges available
        assert analyzer.compute_atr(candles) == []

    def test_matches_hand_calculated_wilder_smoothing(self) -> None:
        offsets = [0.005, 0.008, 0.009, 0.010, 0.007]
        candles = [doji_candle(i, 1.1000, off) for i, off in enumerate(offsets)]
        analyzer = VolatilityAnalyzer(atr_period=2, regime_lookback=2)

        atr_values = analyzer.compute_atr(candles)

        # seed = mean(0.008, 0.009) = 0.0085
        # next  = (0.0085 * 1 + 0.010) / 2 = 0.00925
        # next  = (0.00925 * 1 + 0.007) / 2 = 0.008125
        assert atr_values == pytest.approx([0.0085, 0.00925, 0.008125])


class TestClassifyRegime:
    def setup_method(self) -> None:
        self.analyzer = VolatilityAnalyzer()  # default thresholds: 1.0 / 2.0 / -1.0

    def test_fewer_than_two_values_defaults_to_normal(self) -> None:
        assert self.analyzer.classify_regime([1.0]) == VolatilityRegime.NORMAL
        assert self.analyzer.classify_regime([]) == VolatilityRegime.NORMAL

    def test_insufficient_baseline_defaults_to_normal(self) -> None:
        assert self.analyzer.classify_regime([5.0, 10.0]) == VolatilityRegime.NORMAL

    def test_zero_stdev_baseline_defaults_to_normal(self) -> None:
        baseline = [2.0, 2.0, 2.0, 2.0, 2.0]
        assert self.analyzer.classify_regime(baseline + [2.0]) == VolatilityRegime.NORMAL

    def test_regime_thresholds(self) -> None:
        baseline = [1.0, 2.0, 3.0, 4.0, 5.0]  # mean=3.0, pstdev=sqrt(2)≈1.41421356
        stdev = 2 ** 0.5

        normal = baseline + [3.0]                    # z = 0
        high = baseline + [3.0 + stdev * 1.0]         # z = 1.0
        extreme = baseline + [3.0 + stdev * 2.0]      # z = 2.0
        low = baseline + [3.0 - stdev * 1.0]          # z = -1.0

        assert self.analyzer.classify_regime(normal) == VolatilityRegime.NORMAL
        assert self.analyzer.classify_regime(high) == VolatilityRegime.HIGH
        assert self.analyzer.classify_regime(extreme) == VolatilityRegime.EXTREME
        assert self.analyzer.classify_regime(low) == VolatilityRegime.LOW


class TestAnalyze:
    def test_too_few_candles_returns_empty(self) -> None:
        analyzer = VolatilityAnalyzer(atr_period=5, regime_lookback=2)
        candles = varied_series(5)  # need atr_period + 1 = 6 minimum
        assert analyzer.analyze(candles) == []

    def test_minimal_valid_series_returns_one_reading(self) -> None:
        analyzer = VolatilityAnalyzer(atr_period=5, regime_lookback=2)
        candles = varied_series(6)  # exactly enough for one ATR seed value

        readings = analyzer.analyze(candles)

        assert len(readings) == 1
        assert isinstance(readings[0], VolatilityReading)
        assert readings[0].timestamp == candles[-1].timestamp

    def test_readings_never_look_ahead_and_track_atr_exactly(self) -> None:
        analyzer = VolatilityAnalyzer(atr_period=5, regime_lookback=2)
        candles = varied_series(30)

        atr_values = analyzer.compute_atr(candles)
        readings = analyzer.analyze(candles)

        assert len(readings) == len(atr_values)
        for reading, expected_atr in zip(readings, atr_values):
            assert reading.atr == pytest.approx(expected_atr)
            assert isinstance(reading.regime, VolatilityRegime)

        # The most recent reading must line up with the most recent
        # candle — proves no future data leaked into today's regime call.
        assert readings[-1].timestamp == candles[-1].timestamp