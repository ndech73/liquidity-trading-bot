from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AnalysisEvent:
    event_type: str
    symbol: str
    timeframe: str
    timestamp: datetime
    data: dict[str, Any]
