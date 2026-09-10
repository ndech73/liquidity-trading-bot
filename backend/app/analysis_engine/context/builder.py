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

    def build(self, snapshot, candles: Sequence[Candle]) -> dict:
        # snapshot already has zones/volatility/compression/expansion
        # computed by AnalysisEngine — recomputing liquidity/volatility
        # here from raw candles duplicates that work. Left as-is for now
        # since I don't want to change this pipeline's behavior without
        # you confirming; worth revisiting once structure/analyzer.py is
        # restored, so this can pull from `snapshot` instead of redoing
        # detection from scratch.
        return {
            "liquidity": self.liquidity_detector.detect(candles),
            "volatility": self.volatility_analyzer.analyze(candles),
            "structure": self.structure_analyzer.analyze(candles),
        }