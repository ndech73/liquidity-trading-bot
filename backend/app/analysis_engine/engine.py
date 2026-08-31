from collections.abc import Sequence
from .domain.candle import Candle
from .context.builder import MarketContextBuilder


class AnalysisEngine:
    def __init__(self, context_builder: MarketContextBuilder):
        self.context_builder = context_builder

    def analyze(self, candles: Sequence[Candle]) -> dict:
        if not candles:
            raise ValueError("No market data supplied")
        return self.context_builder.build(candles)
