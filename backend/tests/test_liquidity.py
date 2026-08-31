from datetime import datetime, timedelta, timezone

import pytest

from app.analysis_engine.domain.liquidity import (
    LiquiditySide,
    LiquidityStatus,
    LiquidityType,
    LiquidityZone,
    VolumeNode,
    VolumeProfile,
)


def make_zone(**overrides) -> LiquidityZone:
    data = {
        "symbol": "eurusd",
        "timeframe": "15m",
        "side": LiquiditySide.BUYSIDE,
        "liquidity_type": LiquidityType.SWING_HIGH,
        "price": 1.1050,
        "created_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return LiquidityZone(**data)


def test_zone_normalizes_symbol_to_uppercase():
    zone = make_zone(symbol="eurusd")
    assert zone.symbol == "EURUSD"


def test_zone_generates_id_when_not_provided():
    zone = make_zone()
    assert zone.id
    assert isinstance(zone.id, str)


def test_zone_defaults_to_active_status():
    zone = make_zone()
    assert zone.status == LiquidityStatus.ACTIVE
    assert zone.touches == 1
    assert zone.swept_at is None
    assert zone.sweep_price is None
    assert zone.invalidated_at is None


def test_naive_timestamp_is_normalized_to_utc():
    naive_time = datetime(2026, 1, 1, 12, 0, 0)
    zone = make_zone(created_at=naive_time)
    assert zone.created_at.tzinfo is not None


def test_invalid_price_is_rejected():
    with pytest.raises(ValueError, match="price must be positive"):
        make_zone(price=0)


def test_invalid_touches_is_rejected():
    with pytest.raises(ValueError, match="touches must be at least 1"):
        make_zone(touches=0)


def test_swept_status_requires_swept_fields():
    with pytest.raises(ValueError, match="SWEPT zone must have swept_at and sweep_price"):
        make_zone(status=LiquidityStatus.SWEPT)


def test_swept_fields_require_swept_status():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="only be set when status is SWEPT"):
        make_zone(swept_at=now, sweep_price=1.1055)


def test_invalidated_status_requires_invalidated_at():
    with pytest.raises(ValueError, match="INVALIDATED zone must have invalidated_at"):
        make_zone(status=LiquidityStatus.INVALIDATED)


def test_swept_at_cannot_precede_created_at():
    created = datetime.now(timezone.utc)
    earlier = created - timedelta(hours=1)
    with pytest.raises(ValueError, match="swept_at cannot be before created_at"):
        make_zone(
            created_at=created,
            status=LiquidityStatus.SWEPT,
            swept_at=earlier,
            sweep_price=1.1055,
        )


def test_mark_swept_returns_new_swept_zone():
    zone = make_zone()
    at = zone.created_at + timedelta(hours=1)

    swept_zone = zone.mark_swept(at=at, sweep_price=1.1052)

    assert swept_zone.status == LiquidityStatus.SWEPT
    assert swept_zone.swept_at == at
    assert swept_zone.sweep_price == 1.1052
    # original zone is untouched — mark_swept returns a new object
    assert zone.status == LiquidityStatus.ACTIVE


def test_mark_swept_twice_is_rejected():
    zone = make_zone()
    at = zone.created_at + timedelta(hours=1)
    swept_zone = zone.mark_swept(at=at, sweep_price=1.1052)

    with pytest.raises(ValueError, match="Cannot sweep a zone with status"):
        swept_zone.mark_swept(at=at, sweep_price=1.1052)


def test_mark_invalidated_returns_new_invalidated_zone():
    zone = make_zone()
    at = zone.created_at + timedelta(hours=1)

    invalidated_zone = zone.mark_invalidated(at=at)

    assert invalidated_zone.status == LiquidityStatus.INVALIDATED
    assert invalidated_zone.invalidated_at == at


def test_add_touch_increments_touch_count():
    zone = make_zone()
    touched_zone = zone.add_touch()

    assert touched_zone.touches == 2
    assert zone.touches == 1  # original untouched


def test_add_touch_on_swept_zone_is_rejected():
    zone = make_zone()
    swept_zone = zone.mark_swept(at=zone.created_at, sweep_price=1.1052)

    with pytest.raises(ValueError, match="Cannot add a touch to a zone with status"):
        swept_zone.add_touch()


def test_zone_is_immutable():
    zone = make_zone()
    with pytest.raises(AttributeError):
        zone.price = 1.2000


def make_volume_node(**overrides) -> VolumeNode:
    now = datetime.now(timezone.utc)
    data = {
        "symbol": "eurusd",
        "timeframe": "15m",
        "price": 1.1000,
        "volume": 100.0,
        "period_start": now,
        "period_end": now + timedelta(minutes=15),
    }
    data.update(overrides)
    return VolumeNode(**data)


def test_volume_node_rejects_negative_volume():
    with pytest.raises(ValueError, match="volume cannot be negative"):
        make_volume_node(volume=-10)


def test_volume_profile_requires_at_least_one_node():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="at least one VolumeNode"):
        VolumeProfile(
            symbol="EURUSD",
            timeframe="15m",
            period_start=now,
            period_end=now + timedelta(minutes=15),
            nodes=(),
        )


def test_volume_profile_poc_returns_highest_volume_node():
    now = datetime.now(timezone.utc)
    low_node = make_volume_node(price=1.1000, volume=50.0)
    high_node = make_volume_node(price=1.1010, volume=200.0)

    profile = VolumeProfile(
        symbol="EURUSD",
        timeframe="15m",
        period_start=now,
        period_end=now + timedelta(minutes=15),
        nodes=(low_node, high_node),
    )

    assert profile.poc is high_node


def test_volume_profile_total_volume_sums_all_nodes():
    now = datetime.now(timezone.utc)
    node_a = make_volume_node(price=1.1000, volume=50.0)
    node_b = make_volume_node(price=1.1010, volume=200.0)

    profile = VolumeProfile(
        symbol="EURUSD",
        timeframe="15m",
        period_start=now,
        period_end=now + timedelta(minutes=15),
        nodes=(node_a, node_b),
    )

    assert profile.total_volume == pytest.approx(250.0)