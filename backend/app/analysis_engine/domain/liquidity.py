from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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


@dataclass
class LiquidityZone:
    id: str
    symbol: str
    timeframe: str
    price: float
    liquidity_type: LiquidityType
    created_at: datetime
    status: LiquidityStatus = LiquidityStatus.ACTIVE
    swept_at: datetime | None = None
    sweep_price: float | None = None
