"""Tests for app.analysis_engine.structure.analyzer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.analysis_engine.domain.candle import Candle, Timeframe
from app.analysis_engine.structure.analyzer import (
    MarketStructureTrend,
    StructureAnalyzer,
    StructureReading,
)

START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_zigzag_candles(
    turning_prices: list[float],
    candles_between: int = 5,
    symbol: str = "EURUSD",
) -> list[Candle]:
    """Builds a piecewise-linear zigzag price path through
    `turning_prices` (alternating valley, peak, valley, peak, ...), with
    `candles_between` interpolated candles between each pair. Each
    turning point lands as a genuine local extreme, since the price path
    strictly rises then strictly falls (or vice versa) through it — so
    with the default lookback=2, every turning point is a clean,
    unambiguous swing point.

    Step size between turning points must stay well above the fixed
    +-0.0002 high/low wick offset used below, or adjacent candles could
    tie on high/low and the swing point wouldn't be unambiguous. Keep
    turning_prices spaced by at least ~0.01 to stay safe.
    """
    price_path: list[float] = []
    for idx in range(len(turning_prices) - 1):
        start, end = turning_prices[idx], turning_prices[idx + 1]
        for step in range(candles_between):
            t = step / candles_between
            price_path.append(start + (end - start) * t)
    price_path.append(turning_prices[-1])

    candles = []
    for i, price in enumerate(price_path):
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=Timeframe.M1,
                timestamp=START + timedelta(minutes=i),
                open=price,
                high=price + 0.0002,
                low=price - 0.0002,
                close=price,
            )
        )
    return candles


class TestSwingPointTrendClassification:
    def test_bullish_trend_on_rising_highs_and_lows(self) -> None:
        # valley, peak, valley(higher), peak(higher), valley(higher), peak(higher)
        turning_prices = [1.0900, 1.1000, 1.0950, 1.1100, 1.1050, 1.1200]
        candles = make_zigzag_candles(turning_prices)

        analyzer = StructureAnalyzer(lookback=2)
        readings = analyzer.analyze(candles)

        assert len(readings) > 0
        assert readings[-1].trend == MarketStructureTrend.BULLISH

    def test_bearish_trend_on_falling_highs_and_lows(self) -> None:
        # peak, valley, peak(lower), valley(lower), peak(lower), valley(lower)
        turning_prices = [1.1200, 1.1050, 1.1100, 1.0950, 1.1000, 1.0900]
        candles = make_zigzag_candles(turning_prices)

        analyzer = StructureAnalyzer(lookback=2)
        readings = analyzer.analyze(candles)

        assert len(readings) > 0
        assert readings[-1].trend == MarketStructureTrend.BEARISH

    def test_ranging_on_mixed_higher_high_lower_low(self) -> None:
        # higher high but lower low relative to the previous swing of
        # each type -> neither clean bullish nor bearish
        turning_prices = [1.1000, 1.1050, 1.0900, 1.1200, 1.0850]
        candles = make_zigzag_candles(turning_prices)

        analyzer = StructureAnalyzer(lookback=2)
        readings = analyzer.analyze(candles)

        assert len(readings) > 0
        assert readings[-1].trend == MarketStructureTrend.RANGING

    def test_ranging_when_not_enough_swing_points_yet(self) -> None:
        # Only one full up-down leg -> at most one high and one low
        # confirmed, never two of each, so trend can't be classified.
        turning_prices = [1.1000, 1.1050]
        candles = make_zigzag_candles(turning_prices)

        analyzer = StructureAnalyzer(lookback=2)
        readings = analyzer.analyze(candles)

        assert all(r.trend == MarketStructureTrend.RANGING for r in readings)

    def test_readings_are_returned_in_time_order(self) -> None:
        turning_prices = [1.0900, 1.1000, 1.0950, 1.1100]
        candles = make_zigzag_candles(turning_prices)

        analyzer = StructureAnalyzer(lookback=2)
        readings = analyzer.analyze(candles)

        timestamps = [r.timestamp for r in readings]
        assert timestamps == sorted(timestamps)

    def test_reading_type_is_correct(self) -> None:
        turning_prices = [1.0900, 1.1000, 1.0950, 1.1100]
        candles = make_zigzag_candles(turning_prices)

        analyzer = StructureAnalyzer(lookback=2)
        readings = analyzer.analyze(candles)

        assert all(isinstance(r, StructureReading) for r in readings)


class TestCurrentTrendConvenienceMethod:
    def test_returns_ranging_when_no_swing_points_at_all(self) -> None:
        analyzer = StructureAnalyzer(lookback=2)
        flat_candles = make_zigzag_candles([1.1000, 1.1000])  # no real movement
        assert analyzer.current_trend(flat_candles) == MarketStructureTrend.RANGING

    def test_returns_ranging_on_empty_candles(self) -> None:
        analyzer = StructureAnalyzer(lookback=2)
        assert analyzer.current_trend([]) == MarketStructureTrend.RANGING

    def test_matches_last_reading_when_data_available(self) -> None:
        turning_prices = [1.0900, 1.1000, 1.0950, 1.1100, 1.1050, 1.1200]
        candles = make_zigzag_candles(turning_prices)

        analyzer = StructureAnalyzer(lookback=2)
        readings = analyzer.analyze(candles)

        assert analyzer.current_trend(candles) == readings[-1].trend


class TestConstructorValidation:
    def test_lookback_below_one_raises(self) -> None:
        with pytest.raises(ValueError):
            StructureAnalyzer(lookback=0)

    def test_default_lookback_matches_liquidity_detector_default(self) -> None:
        # Both modules should agree on what counts as a swing point by
        # default, so keep their default lookback values in sync.
        analyzer = StructureAnalyzer()
        assert analyzer.lookback == 2