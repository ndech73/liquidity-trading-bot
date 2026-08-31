from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from app.analysis_engine.domain.candle import Timeframe


class LiquiditySide(str, Enum):
    BUYSIDE = "buyside"
    SELLSIDE = "sellside"


class LiquidityType(str, Enum):
    SWING_HIGH = "swing_high"
    SWING_LOW = "swing_low"
    EQUAL_HIGH = "equal_high"
    EQUAL_LOW = "equal_low"
    SESSION_HIGH = "session_high"
    SESSION_LOW = "session_low"
    PREVIOUS_HIGH = "previous_high"
    PREVIOUS_LOW = "previous_low"


class LiquidityStatus(str, Enum):
    ACTIVE = "active"
    SWEPT = "swept"
    INVALIDATED = "invalidated"


@dataclass(frozen=True, slots=True)
class LiquidityZone:
    symbol: str
    timeframe: Timeframe
    side: LiquiditySide
    liquidity_type: LiquidityType
    price: float
    created_at: datetime
    id: str = field(default_factory=lambda: str(uuid4()))
    status: LiquidityStatus = LiquidityStatus.ACTIVE
    touches: int = 1
    swept_at: datetime | None = None
    sweep_price: float | None = None
    invalidated_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("LiquidityZone symbol cannot be empty")
        if not self.id:
            raise ValueError("LiquidityZone id cannot be empty")

        object.__setattr__(self, "symbol", self.symbol.upper())
        object.__setattr__(self, "timeframe", Timeframe(self.timeframe))

        if self.created_at.tzinfo is None:
            object.__setattr__(
                self, "created_at", self.created_at.replace(tzinfo=timezone.utc)
            )
        if self.swept_at is not None and self.swept_at.tzinfo is None:
            object.__setattr__(
                self, "swept_at", self.swept_at.replace(tzinfo=timezone.utc)
            )
        if self.invalidated_at is not None and self.invalidated_at.tzinfo is None:
            object.__setattr__(
                self, "invalidated_at", self.invalidated_at.replace(tzinfo=timezone.utc)
            )

        if self.price <= 0:
            raise ValueError(f"LiquidityZone price must be positive ({self.price})")
        if self.touches < 1:
            raise ValueError("LiquidityZone touches must be at least 1")

        if self.status == LiquidityStatus.SWEPT:
            if self.swept_at is None or self.sweep_price is None:
                raise ValueError("A SWEPT zone must have swept_at and sweep_price set")
        else:
            if self.swept_at is not None or self.sweep_price is not None:
                raise ValueError("swept_at/sweep_price can only be set when status is SWEPT")

        if self.status == LiquidityStatus.INVALIDATED:
            if self.invalidated_at is None:
                raise ValueError("An INVALIDATED zone must have invalidated_at set")
        else:
            if self.invalidated_at is not None:
                raise ValueError("invalidated_at can only be set when status is INVALIDATED")

        if self.swept_at is not None and self.swept_at < self.created_at:
            raise ValueError("swept_at cannot be before created_at")
        if self.invalidated_at is not None and self.invalidated_at < self.created_at:
            raise ValueError("invalidated_at cannot be before created_at")

    def mark_swept(self, at: datetime, sweep_price: float) -> "LiquidityZone":
        if self.status != LiquidityStatus.ACTIVE:
            raise ValueError(f"Cannot sweep a zone with status {self.status}")
        return replace(self, status=LiquidityStatus.SWEPT, swept_at=at, sweep_price=sweep_price)

    def mark_invalidated(self, at: datetime) -> "LiquidityZone":
        if self.status != LiquidityStatus.ACTIVE:
            raise ValueError(f"Cannot invalidate a zone with status {self.status}")
        return replace(self, status=LiquidityStatus.INVALIDATED, invalidated_at=at)

    def add_touch(self) -> "LiquidityZone":
        if self.status != LiquidityStatus.ACTIVE:
            raise ValueError(f"Cannot add a touch to a zone with status {self.status}")
        return replace(self, touches=self.touches + 1)


@dataclass(frozen=True, slots=True)
class VolumeNode:
    """Traded volume at a single price level within a period."""

    symbol: str
    timeframe: Timeframe
    price: float
    volume: float
    period_start: datetime
    period_end: datetime

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("VolumeNode symbol cannot be empty")

        object.__setattr__(self, "symbol", self.symbol.upper())
        object.__setattr__(self, "timeframe", Timeframe(self.timeframe))

        if self.period_start.tzinfo is None:
            object.__setattr__(
                self, "period_start", self.period_start.replace(tzinfo=timezone.utc)
            )
        if self.period_end.tzinfo is None:
            object.__setattr__(
                self, "period_end", self.period_end.replace(tzinfo=timezone.utc)
            )

        if self.price <= 0:
            raise ValueError(f"VolumeNode price must be positive ({self.price})")
        if self.volume < 0:
            raise ValueError("VolumeNode volume cannot be negative")
        if self.period_end < self.period_start:
            raise ValueError("period_end cannot be before period_start")


@dataclass(frozen=True, slots=True)
class VolumeProfile:
    """A full volume-by-price distribution for a period, with VPOC lookup."""

    symbol: str
    timeframe: Timeframe
    period_start: datetime
    period_end: datetime
    nodes: tuple[VolumeNode, ...]

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("VolumeProfile symbol cannot be empty")
        if not self.nodes:
            raise ValueError("VolumeProfile must contain at least one VolumeNode")

        object.__setattr__(self, "symbol", self.symbol.upper())
        object.__setattr__(self, "timeframe", Timeframe(self.timeframe))
        object.__setattr__(self, "nodes", tuple(self.nodes))

        if self.period_start.tzinfo is None:
            object.__setattr__(
                self, "period_start", self.period_start.replace(tzinfo=timezone.utc)
            )
        if self.period_end.tzinfo is None:
            object.__setattr__(
                self, "period_end", self.period_end.replace(tzinfo=timezone.utc)
            )
        if self.period_end < self.period_start:
            raise ValueError("period_end cannot be before period_start")

    @property
    def poc(self) -> VolumeNode:
        """Volume Point of Control — the price level with the highest traded volume."""
        return max(self.nodes, key=lambda node: node.volume)

    @property
    def total_volume(self) -> float:
        return sum(node.volume for node in self.nodes)