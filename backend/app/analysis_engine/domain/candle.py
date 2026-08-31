from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


@dataclass(frozen=True, slots=True)
class Candle:
    symbol: str
    timeframe: Timeframe
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("Candle symbol cannot be empty")

        object.__setattr__(self, "symbol", self.symbol.upper())
        object.__setattr__(self, "timeframe", Timeframe(self.timeframe))

        if self.timestamp.tzinfo is None:
            object.__setattr__(
                self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc)
            )

        if self.low < 0:
            raise ValueError(f"Candle low cannot be negative ({self.low})")
        if self.high < self.low:
            raise ValueError("Candle high cannot be lower than low")
        if self.open < self.low or self.open > self.high:
            raise ValueError("Candle open must be between low and high")
        if self.close < self.low or self.close > self.high:
            raise ValueError("Candle close must be between low and high")
        if self.volume is not None and self.volume < 0:
            raise ValueError("Candle volume cannot be negative")

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def bullish(self) -> bool:
        return self.close > self.open

    @property
    def bearish(self) -> bool:
        return self.close < self.open

    def is_doji(self, tolerance: float = 0.1) -> bool:
        if self.range == 0:
            return True
        return self.body / self.range < tolerance

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe.value,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Candle":
        return cls(
            symbol=data["symbol"],
            timeframe=Timeframe(data["timeframe"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=(
                float(data["volume"]) if data.get("volume") is not None else None
            ),
        )