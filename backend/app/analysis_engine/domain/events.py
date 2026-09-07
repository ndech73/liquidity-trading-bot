from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from app.analysis_engine.domain.candle import Timeframe
from app.analysis_engine.domain.liquidity import LiquiditySide, LiquidityType


class SweepDetectionSource(str, Enum):
    """Which pipeline caught the sweep. TICK means it was flagged the
    instant price crossed the level, before any candle closed — CANDLE
    means it was found by scanning closed OHLCV bars."""

    CANDLE = "candle"
    TICK = "tick"


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base class every event shares: what symbol/timeframe it applies to,
    and exactly when it happened."""

    symbol: str
    timeframe: Timeframe
    occurred_at: datetime

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError(f"{type(self).__name__} symbol cannot be empty")

        object.__setattr__(self, "symbol", self.symbol.upper())
        object.__setattr__(self, "timeframe", Timeframe(self.timeframe))

        if self.occurred_at.tzinfo is None:
            object.__setattr__(
                self, "occurred_at", self.occurred_at.replace(tzinfo=timezone.utc)
            )


@dataclass(frozen=True, slots=True)
class LiquiditySweepEvent(DomainEvent):
    """Fired when a LiquidityZone gets swept — price ran through a resting
    stop cluster."""

    zone_id: str
    side: LiquiditySide
    liquidity_type: LiquidityType
    level_price: float
    sweep_price: float
    detected_via: SweepDetectionSource = SweepDetectionSource.CANDLE

    def __post_init__(self) -> None:
        DomainEvent.__post_init__(self)

        if not self.zone_id:
            raise ValueError("LiquiditySweepEvent zone_id cannot be empty")
        if self.level_price <= 0:
            raise ValueError("LiquiditySweepEvent level_price must be positive")
        if self.sweep_price <= 0:
            raise ValueError("LiquiditySweepEvent sweep_price must be positive")

        object.__setattr__(
            self, "detected_via", SweepDetectionSource(self.detected_via)
        )