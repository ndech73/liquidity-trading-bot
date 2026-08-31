from datetime import datetime, timedelta, timezone

import pytest

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.domain.liquidity import LiquiditySide, LiquidityType
from app.analysis_engine.liquidity.detector import LiquidityDetector


def make_candles(highs, lows, opens=None, closes=None) -> list[Candle]:
    """Build a simple candle series from parallel lists of highs/lows."""
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    for i, (h, l) in enumerate(zip(highs, lows)):
        o = opens[i] if opens else (h + l) / 2
        c = closes[i] if closes else (h + l) / 2
        candles.append(
            Candle(
                symbol="EURUSD",
                timeframe="15m",
                timestamp=start + timedelta(minutes=15 * i),
                open=o,
                high=h,
                low=l,
                close=c,
            )
        )
    return candles


def test_detects_a_simple_swing_high():
    # index 2 is the highest point, surrounded by lower highs on each side
    highs = [1.1000, 1.1010, 1.1050, 1.1005, 1.0995]
    lows =  [1.0990, 1.1000, 1.1030, 1.0990, 1.0980]
    candles = make_candles(highs, lows)

    detector = LiquidityDetector(lookback=2)
    zones = detector.detect(candles)

    swing_highs = [z for z in zones if z.liquidity_type == LiquidityType.SWING_HIGH]
    assert len(swing_highs) == 1
    assert swing_highs[0].price == pytest.approx(1.1050)
    assert swing_highs[0].side == LiquiditySide.BUYSIDE


def test_detects_a_simple_swing_low():
    highs = [1.1020, 1.1010, 1.0990, 1.1005, 1.1015]
    lows =  [1.1000, 1.0995, 1.0940, 1.0990, 1.1000]
    candles = make_candles(highs, lows)

    detector = LiquidityDetector(lookback=2)
    zones = detector.detect(candles)

    swing_lows = [z for z in zones if z.liquidity_type == LiquidityType.SWING_LOW]
    assert len(swing_lows) == 1
    assert swing_lows[0].price == pytest.approx(1.0940)
    assert swing_lows[0].side == LiquiditySide.SELLSIDE


def test_too_few_candles_returns_no_zones():
    highs = [1.1000, 1.1010]
    lows = [1.0990, 1.1000]
    candles = make_candles(highs, lows)

    detector = LiquidityDetector(lookback=2)
    zones = detector.detect(candles)

    assert zones == []


def test_merges_two_nearby_swing_highs_into_equal_high():
    # Two separate swing highs at ~1.1050, close enough to count as "equal"
    highs = [
        1.1000, 1.1010, 1.1050, 1.1005, 1.0995,
        1.1000, 1.1010, 1.1051, 1.1005, 1.0995,
    ]
    lows = [
        1.0990, 1.1000, 1.1030, 1.0990, 1.0980,
        1.0990, 1.1000, 1.1030, 1.0990, 1.0980,
    ]
    candles = make_candles(highs, lows)

    detector = LiquidityDetector(lookback=2, equal_level_tolerance_pct=0.001)
    zones = detector.detect(candles)

    equal_highs = [z for z in zones if z.liquidity_type == LiquidityType.EQUAL_HIGH]
    swing_highs = [z for z in zones if z.liquidity_type == LiquidityType.SWING_HIGH]

    assert len(equal_highs) == 1
    assert len(swing_highs) == 0
    assert equal_highs[0].touches == 2
    assert equal_highs[0].price == pytest.approx((1.1050 + 1.1051) / 2)


def test_distant_swing_highs_are_not_merged():
    highs = [
        1.1000, 1.1010, 1.1050, 1.1005, 1.0995,
        1.1000, 1.1010, 1.1200, 1.1005, 1.0995,
    ]
    lows = [
        1.0990, 1.1000, 1.1030, 1.0990, 1.0980,
        1.0990, 1.1000, 1.1030, 1.0990, 1.0980,
    ]
    candles = make_candles(highs, lows)

    detector = LiquidityDetector(lookback=2, equal_level_tolerance_pct=0.0005)
    zones = detector.detect(candles)

    swing_highs = [z for z in zones if z.liquidity_type == LiquidityType.SWING_HIGH]
    equal_highs = [z for z in zones if z.liquidity_type == LiquidityType.EQUAL_HIGH]

    assert len(swing_highs) == 2
    assert len(equal_highs) == 0