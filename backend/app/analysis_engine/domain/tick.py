from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class Tick:
    """A single bid/ask update for a symbol, at millisecond precision.
    This is the raw unit the tick feed pushes into detectors that need
    to react faster than a candle close allows."""

    symbol: str
    timestamp: datetime
    bid: float
    ask: float

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("Tick symbol cannot be empty")

        object.__setattr__(self, "symbol", self.symbol.upper())

        if self.timestamp.tzinfo is None:
            object.__setattr__(
                self, "timestamp", self.timestamp.replace(tzinfo=timezone.utc)
            )

        if self.bid <= 0:
            raise ValueError(f"Tick bid must be positive ({self.bid})")
        if self.ask <= 0:
            raise ValueError(f"Tick ask must be positive ({self.ask})")
        if self.ask < self.bid:
            raise ValueError("Tick ask cannot be less than bid")

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> float:
        return self.ask - self.bid