from datetime import datetime, timedelta, timezone

import pytest

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.domain.events import SweepDetectionSource
from app.analysis_engine.domain.liquidity import (
    LiquiditySide,
    LiquidityStatus,
    LiquidityType,
    LiquidityZone,
)
from app.analysis_engine.domain.tick import Tick
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


def make_tick(timestamp, bid, ask, symbol="EURUSD") -> Tick:
    return Tick(symbol=symbol, timestamp=timestamp, bid=bid, ask=ask)


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
    assert events[0].detected_via == SweepDetectionSource.CANDLE


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


# ---------------------------------------------------------------------
# detect_tick() — tick-based sweep detection with penetration/hold filters
# ---------------------------------------------------------------------


def test_tick_sweep_fires_instantly_when_filters_are_zero():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=1),
        bid=1.1049,
        ask=1.1052,  # ask past the buyside level
    )

    detector = SweepDetector(min_penetration=0.0, min_hold_seconds=0.0)
    updated_zones, events = detector.detect_tick([zone], tick)

    assert updated_zones[0].status == LiquidityStatus.SWEPT
    assert updated_zones[0].sweep_price == pytest.approx(1.1052)
    assert len(events) == 1
    assert events[0].detected_via == SweepDetectionSource.TICK
    assert events[0].occurred_at == tick.timestamp


def test_sellside_tick_sweep_uses_bid():
    zone = make_zone(
        side=LiquiditySide.SELLSIDE,
        liquidity_type=LiquidityType.SWING_LOW,
        price=1.0950,
    )
    tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=1),
        bid=1.0948,  # bid past the sellside level
        ask=1.0951,
    )

    detector = SweepDetector(min_penetration=0.0, min_hold_seconds=0.0)
    updated_zones, events = detector.detect_tick([zone], tick)

    assert updated_zones[0].status == LiquidityStatus.SWEPT
    assert updated_zones[0].sweep_price == pytest.approx(1.0948)


def test_tick_that_has_not_reached_the_level_does_not_sweep():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=1),
        bid=1.1040,
        ask=1.1045,  # still below the level
    )

    detector = SweepDetector()
    updated_zones, events = detector.detect_tick([zone], tick)

    assert updated_zones[0].status == LiquidityStatus.ACTIVE
    assert events == []


def test_tick_below_min_penetration_does_not_sweep_yet():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=1),
        bid=1.1050,
        ask=1.1051,  # only 1 pip past the level
    )

    detector = SweepDetector(min_penetration=0.0005, min_hold_seconds=0.0)
    updated_zones, events = detector.detect_tick([zone], tick)

    assert updated_zones[0].status == LiquidityStatus.ACTIVE
    assert events == []


def test_tick_sweep_fires_once_penetration_and_hold_are_both_satisfied():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    detector = SweepDetector(min_penetration=0.0005, min_hold_seconds=2.0)

    # First tick crosses far enough, but hold time hasn't accumulated yet.
    first_tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=1),
        bid=1.1054,
        ask=1.1056,
    )
    zones_after_first, events_after_first = detector.detect_tick([zone], first_tick)
    assert zones_after_first[0].status == LiquidityStatus.ACTIVE
    assert events_after_first == []

    # Second tick, 3 seconds later, still past the level -> hold satisfied.
    second_tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=4),
        bid=1.1054,
        ask=1.1056,
    )
    zones_after_second, events_after_second = detector.detect_tick(
        zones_after_first, second_tick
    )

    assert zones_after_second[0].status == LiquidityStatus.SWEPT
    assert len(events_after_second) == 1
    # occurred_at should be the FIRST crossing time, not the confirming tick
    assert events_after_second[0].occurred_at == first_tick.timestamp


def test_price_retreating_before_hold_time_resets_the_pending_crossing():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    detector = SweepDetector(min_penetration=0.0005, min_hold_seconds=2.0)

    crossing_tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=1),
        bid=1.1054,
        ask=1.1056,
    )
    zones_after_cross, _ = detector.detect_tick([zone], crossing_tick)
    assert zones_after_cross[0].status == LiquidityStatus.ACTIVE

    # Price snaps back below the level before hold time is reached.
    retreat_tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=2),
        bid=1.1040,
        ask=1.1042,
    )
    zones_after_retreat, events_after_retreat = detector.detect_tick(
        zones_after_cross, retreat_tick
    )
    assert zones_after_retreat[0].status == LiquidityStatus.ACTIVE
    assert events_after_retreat == []

    # Crossing again should restart the hold clock, not resume the old one.
    recross_tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=3),
        bid=1.1054,
        ask=1.1056,
    )
    zones_after_recross, events_after_recross = detector.detect_tick(
        zones_after_retreat, recross_tick
    )
    # Only 0 seconds held since the recross -> should not fire yet.
    assert zones_after_recross[0].status == LiquidityStatus.ACTIVE
    assert events_after_recross == []


def test_tick_for_a_different_symbol_is_ignored():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=1),
        bid=1.1049,
        ask=1.1052,
        symbol="GBPUSD",
    )

    detector = SweepDetector(min_penetration=0.0, min_hold_seconds=0.0)
    updated_zones, events = detector.detect_tick([zone], tick)

    assert updated_zones[0].status == LiquidityStatus.ACTIVE
    assert events == []


def test_tick_at_or_before_zone_creation_is_ignored():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    tick = make_tick(
        timestamp=zone.created_at,  # same timestamp as zone formation
        bid=1.1049,
        ask=1.1052,
    )

    detector = SweepDetector(min_penetration=0.0, min_hold_seconds=0.0)
    updated_zones, events = detector.detect_tick([zone], tick)

    assert updated_zones[0].status == LiquidityStatus.ACTIVE
    assert events == []


def test_already_swept_zone_is_left_untouched_by_ticks():
    zone = make_zone(side=LiquiditySide.BUYSIDE, price=1.1050)
    swept_zone = zone.mark_swept(
        at=zone.created_at + timedelta(seconds=1), sweep_price=1.1060
    )
    later_tick = make_tick(
        timestamp=zone.created_at + timedelta(seconds=2),
        bid=1.1049,
        ask=1.1070,
    )

    detector = SweepDetector(min_penetration=0.0, min_hold_seconds=0.0)
    updated_zones, events = detector.detect_tick([swept_zone], later_tick)

    assert updated_zones[0] is swept_zone
    assert events == []