from datetime import datetime, timedelta, timezone

import pytest

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.volatility.compression import CompressionDetector


def make_range_candles(ranges: list[float]) -> list[Candle]:
    """Build a candle series where the true range of candle i (for i>0)
    equals ranges[i]. ranges[0] only anchors the starting price and is
    not itself measured (True Range skips the first candle)."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    price = 1.1000
    for i, r in enumerate(ranges):
        low = price
        high = price + r
        candles.append(
            Candle(
                symbol="EURUSD",
                timeframe="15m",
                timestamp=start + timedelta(minutes=15 * i),
                open=low,
                high=high,
                low=low,
                close=high,
            )
        )
        price = high
    return candles


def test_detects_compression_when_recent_range_shrinks_sharply():
    # anchor + 5 baseline candles at 0.0020 range + 3 recent candles at 0.0004 range
    ranges = [0.0010] + [0.0020] * 5 + [0.0004] * 3
    candles = make_range_candles(ranges)

    detector = CompressionDetector(recent_window=3, baseline_window=5)
    readings = detector.analyze(candles)

    assert len(readings) == 1
    reading = readings[0]
    assert reading.is_compressed is True
    assert reading.recent_avg_range == pytest.approx(0.0004)
    assert reading.baseline_avg_range == pytest.approx(0.0020)
    assert reading.contraction_ratio == pytest.approx(0.2)


def test_does_not_flag_compression_when_ranges_are_similar():
    ranges = [0.0010] + [0.0010] * 5 + [0.0010] * 3
    candles = make_range_candles(ranges)

    detector = CompressionDetector(recent_window=3, baseline_window=5)
    readings = detector.analyze(candles)

    assert len(readings) == 1
    assert readings[0].is_compressed is False
    assert readings[0].contraction_ratio == pytest.approx(1.0)


def test_too_few_candles_returns_no_readings():
    ranges = [0.0010] * 4  # far short of recent_window + baseline_window
    candles = make_range_candles(ranges)

    detector = CompressionDetector(recent_window=3, baseline_window=5)
    readings = detector.analyze(candles)

    assert readings == []


def test_is_currently_compressed_convenience_method():
    compressed_ranges = [0.0010] + [0.0020] * 5 + [0.0004] * 3
    compressed_candles = make_range_candles(compressed_ranges)

    flat_ranges = [0.0010] + [0.0010] * 5 + [0.0010] * 3
    flat_candles = make_range_candles(flat_ranges)

    detector = CompressionDetector(recent_window=3, baseline_window=5)

    assert detector.is_currently_compressed(compressed_candles) is True
    assert detector.is_currently_compressed(flat_candles) is False