from collections.abc import Sequence
from ..domain.candle import Candle
from ..domain.liquidity import LiquidityZone


class LiquidityDetector:
    def detect(self, candles: Sequence[Candle]) -> list[LiquidityZone]:
        # Research implementation starts here.
        # Keep each liquidity definition as a separate detector.
        return []
