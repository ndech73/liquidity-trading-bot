from collections.abc import Sequence
from ..domain.candle import Candle


class StructureAnalyzer:
    def analyze(self, candles: Sequence[Candle]) -> dict:
        # Add swing-high/swing-low and HH/HL/LH/LL research here.
        return {
            "trend_structure": None,
            "swing_highs": [],
            "swing_lows": [],
        }
