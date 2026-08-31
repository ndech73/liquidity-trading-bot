from collections.abc import Sequence
from ..domain.candle import Candle


class VolatilityAnalyzer:
    def analyze(self, candles: Sequence[Candle]) -> dict[str, float | None]:
        ranges = [c.range for c in candles]
        if not ranges:
            return {"current_range": None, "average_range": None, "expansion_ratio": None}

        current = ranges[-1]
        average = sum(ranges) / len(ranges)
        ratio = current / average if average else None

        return {
            "current_range": current,
            "average_range": average,
            "expansion_ratio": ratio,
        }
