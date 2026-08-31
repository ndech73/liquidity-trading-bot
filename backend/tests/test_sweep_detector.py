from datetime import datetime, timedelta, timezone

import pytest

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.domain.liquidity import (
    LiquiditySide,
    LiquidityStatus,
    LiquidityType,
    LiquidityZone,
)
from app.analysis_engine.liquidity.sweep_detector import SweepDetector


def make_candle(timestamp, open_, high, low, close) -> Candle:
    return Candle(
        symbol="EURUSD",
        timeframe="15m",
        timestamp=timestamp,
        open=open_,
        high=high,
        low=low,
        close=close,
    )


def make_zone(**overrides) -> LiquidityZone:
    data = {
        "symbol": "eurusd",
        "timeframe": "15m",
        "side": LiquiditySide.BUYSIDE,
        "liquidity_type": LiquidityType.SWING_HIGH,
        "price": 1.1050,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    data.update(overrides)
    return LiquidityZone(**data)


def test_buyside_zone_is_swept_when_price_pierces_and_closes_back_below():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    sweep_candle = make_candle(
        timestamp=zone.created_at + timedelta(minutes=15),
        open_=1.1040,
        high=1.1060,   # pierces above the zone
        low=1.1035,
        close=1.1045,  # closes back below the zone
    )

    detector = SweepDetector()
    updated_zones, events = detector.detect([zone], [sweep_candle])

    assert updated_zones[0].status == LiquidityStatus.SWEPT
    assert updated_zones[0].sweep_price == pytest.approx(1.1060)
    assert len(events) == 1
    assert events[0].zone_id == zone.id
    assert events[0].sweep_price == pytest.approx(1.1060)


def test_sellside_zone_is_swept_when_price_pierces_and_closes_back_above():
    zone = make_zone(
        side=LiquiditySide.SELLSIDE,
        liquidity_type=LiquidityType.SWING_LOW,
        price=1.0950,
    )
    sweep_candle = make_candle(
        timestamp=zone.created_at + timedelta(minutes=15),
        open_=1.0960,
        high=1.0965,
        low=1.0940,   # pierces below the zone
        close=1.0955, # closes back above the zone
    )

    detector = SweepDetector()
    updated_zones, events = detector.detect([zone], [sweep_candle])

    assert updated_zones[0].status == LiquidityStatus.SWEPT
    assert updated_zones[0].sweep_price == pytest.approx(1.0940)
    assert len(events) == 1


def test_pierce_without_close_back_is_not_a_sweep():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    breakout_candle = make_candle(
        timestamp=zone.created_at + timedelta(minutes=15),
        open_=1.1040,
        high=1.1080,
        low=1.1035,
        close=1.1075,  # closes ABOVE the zone — continuation, not a sweep
    )

    detector = SweepDetector()
    updated_zones, events = detector.detect([zone], [breakout_candle])

    assert updated_zones[0].status == LiquidityStatus.ACTIVE
    assert events == []


def test_candle_at_or_before_zone_creation_is_ignored():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    same_candle = make_candle(
        timestamp=zone.created_at,  # same timestamp as zone formation
        open_=1.1040,
        high=1.1060,
        low=1.1035,
        close=1.1045,
    )

    detector = SweepDetector()
    updated_zones, events = detector.detect([zone], [same_candle])

    assert updated_zones[0].status == LiquidityStatus.ACTIVE
    assert events == []


def test_already_swept_zone_is_left_untouched():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    swept_zone = zone.mark_swept(
        at=zone.created_at + timedelta(minutes=15), sweep_price=1.1060
    )
    later_candle = make_candle(
        timestamp=zone.created_at + timedelta(minutes=30),
        open_=1.1040,
        high=1.1070,
        low=1.1035,
        close=1.1045,
    )

    detector = SweepDetector()
    updated_zones, events = detector.detect([swept_zone], [later_candle])

    assert updated_zones[0] is swept_zone
    assert events == []


def test_first_qualifying_candle_wins():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    first_sweep = make_candle(
        timestamp=zone.created_at + timedelta(minutes=15),
        open_=1.1040,
        high=1.1055,
        low=1.1035,
        close=1.1045,
    )
    second_sweep = make_candle(
        timestamp=zone.created_at + timedelta(minutes=30),
        open_=1.1040,
        high=1.1090,
        low=1.1035,
        close=1.1045,
    )

    detector = SweepDetector()
    updated_zones, events = detector.detect([zone], [first_sweep, second_sweep])

    assert updated_zones[0].sweep_price == pytest.approx(1.1055)
    assert len(events) == 1