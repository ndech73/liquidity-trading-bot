from datetime import datetime, timedelta, timezone

import pytest

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.volatility.expansion import ExpansionDetector, ExpansionDirection


def make_directional_candles(ranges: list[float], bullish: bool = True) -> list[Candle]:
    """Build a candle series where the true range of candle i (for i>0)
    equals ranges[i], with every candle's body fully in the given
    direction (so price moves monotonically bullish or bearish)."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    price = 1.1000
    for i, r in enumerate(ranges):
        if bullish:
            low = price
            high = price + r
            open_, close = low, high
            next_price = high
        else:
            high = price
            low = price - r
            open_, close = high, low
            next_price = low
        candles.append(
            Candle(
                symbol="EURUSD",
                timeframe="15m",
                timestamp=start + timedelta(minutes=15 * i),
                open=open_,
                high=high,
                low=low,
                close=close,
            )
        )
        price = next_price
    return candles


def test_detects_expansion_with_bullish_direction():
    # anchor + 5 baseline candles at 0.0005 range + 3 recent candles at 0.0025 range
    ranges = [0.0005] + [0.0005] * 5 + [0.0025] * 3
    candles = make_directional_candles(ranges, bullish=True)

    detector = ExpansionDetector(recent_window=3, baseline_window=5)
    readings = detector.analyze(candles)

    assert len(readings) == 1
    reading = readings[0]
    assert reading.is_expanding is True
    assert reading.recent_avg_range == pytest.approx(0.0025)
    assert reading.baseline_avg_range == pytest.approx(0.0005)
    assert reading.expansion_ratio == pytest.approx(5.0)
    assert reading.direction == ExpansionDirection.BULLISH


def test_detects_expansion_with_bearish_direction():
    ranges = [0.0005] + [0.0005] * 5 + [0.0025] * 3
    candles = make_directional_candles(ranges, bullish=False)

    detector = ExpansionDetector(recent_window=3, baseline_window=5)
    readings = detector.analyze(candles)

    assert len(readings) == 1
    assert readings[0].is_expanding is True
    assert readings[0].direction == ExpansionDirection.BEARISH


def test_does_not_flag_expansion_when_ranges_are_similar():
    ranges = [0.0010] + [0.0010] * 5 + [0.0010] * 3
    candles = make_directional_candles(ranges, bullish=True)

    detector = ExpansionDetector(recent_window=3, baseline_window=5)
    readings = detector.analyze(candles)

    assert len(readings) == 1
    assert readings[0].is_expanding is False


def test_choppy_expansion_is_classified_neutral():
    # anchor + 4 small monotonic baseline candles, then a zigzag of 4
    # large candles (up, down, up, down) that net out to ~zero movement.
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    price = 1.1000

    def add_candle(i, low, high, open_, close):
        candles.append(
            Candle(
                symbol="EURUSD",
                timeframe="15m",
                timestamp=start + timedelta(minutes=15 * i),
                open=open_,
                high=high,
                low=low,
                close=close,
            )
        )

    # anchor candle (not itself measured by True Range)
    low, high = price, price + 0.0005
    add_candle(0, low, high, low, high)
    price = high

    # baseline: 4 small monotonic (bullish) candles
    for i in range(1, 5):
        low, high = price, price + 0.0005
        add_candle(i, low, high, low, high)
        price = high

    # recent: zigzag of 4 large candles, alternating direction, net ~0
    for j, bullish in enumerate([True, False, True, False]):
        i = 5 + j
        if bullish:
            low, high = price, price + 0.0025
            open_, close = low, high
            price = high
        else:
            high, low = price, price - 0.0025
            open_, close = high, low
            price = low
        add_candle(i, low, high, open_, close)

    detector = ExpansionDetector(recent_window=4, baseline_window=4)
    readings = detector.analyze(candles)

    assert len(readings) == 1
    assert readings[0].is_expanding is True
    assert readings[0].direction == ExpansionDirection.NEUTRAL


def test_too_few_candles_returns_no_readings():
    ranges = [0.0010] * 4
    candles = make_directional_candles(ranges, bullish=True)

    detector = ExpansionDetector(recent_window=3, baseline_window=5)
    readings = detector.analyze(candles)

    assert readings == []


def test_is_currently_expanding_convenience_method():
    expanding_ranges = [0.0005] + [0.0005] * 5 + [0.0025] * 3
    expanding_candles = make_directional_candles(expanding_ranges, bullish=True)

    flat_ranges = [0.0010] + [0.0010] * 5 + [0.0010] * 3
    flat_candles = make_directional_candles(flat_ranges, bullish=True)

    detector = ExpansionDetector(recent_window=3, baseline_window=5)

    assert detector.is_currently_expanding(expanding_candles) is True
    assert detector.is_currently_expanding(flat_candles) is False