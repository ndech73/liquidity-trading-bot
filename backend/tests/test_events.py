from datetime import datetime, timezone

import pytest

from app.analysis_engine.domain.events import LiquiditySweepEvent
from app.analysis_engine.domain.liquidity import LiquiditySide, LiquidityType


def make_sweep_event(**overrides) -> LiquiditySweepEvent:
    data = {
        "symbol": "eurusd",
        "timeframe": "15m",
        "occurred_at": datetime.now(timezone.utc),
        "zone_id": "zone-123",
        "side": LiquiditySide.BUYSIDE,
        "liquidity_type": LiquidityType.SWING_HIGH,
        "level_price": 1.1050,
        "sweep_price": 1.1055,
    }
    data.update(overrides)
    return LiquiditySweepEvent(**data)


def test_sweep_event_normalizes_symbol_and_timeframe():
    event = make_sweep_event(symbol="eurusd", timeframe="15m")
    assert event.symbol == "EURUSD"
    assert event.timeframe.value == "15m"


def test_sweep_event_requires_zone_id():
    with pytest.raises(ValueError, match="zone_id cannot be empty"):
        make_sweep_event(zone_id="")


def test_sweep_event_rejects_non_positive_level_price():
    with pytest.raises(ValueError, match="level_price must be positive"):
        make_sweep_event(level_price=0)


def test_sweep_event_rejects_non_positive_sweep_price():
    with pytest.raises(ValueError, match="sweep_price must be positive"):
        make_sweep_event(sweep_price=-1)


def test_sweep_event_is_immutable():
    event = make_sweep_event()
    with pytest.raises(AttributeError):
        event.sweep_price = 1.2000