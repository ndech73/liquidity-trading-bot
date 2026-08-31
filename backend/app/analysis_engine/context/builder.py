from collections.abc import Sequence
from ..domain.candle import Candle
from ..liquidity.detector import LiquidityDetector
from ..structure.analyzer import StructureAnalyzer
from ..volatility.analyzer import VolatilityAnalyzer


class MarketContextBuilder:
    def __init__(
        self,
        liquidity_detector: LiquidityDetector,
        volatility_analyzer: VolatilityAnalyzer,
        structure_analyzer: StructureAnalyzer,
    ):
        self.liquidity_detector = liquidity_detector
        self.volatility_analyzer = volatility_analyzer
        self.structure_analyzer = structure_analyzer

    def build(self, candles: Sequence[Candle]) -> dict:
        return {
            "liquidity": self.liquidity_detector.detect(candles),
            "volatility": self.volatility_analyzer.analyze(candles),
            "structure": self.structure_analyzer.analyze(candles),
        }
