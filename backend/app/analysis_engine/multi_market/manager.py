from __future__ import annotations

from dataclasses import dataclass, field

from app.analysis_engine.domain.candle import Timeframe
from app.analysis_engine.domain.events import LiquiditySweepEvent
from app.analysis_engine.domain.liquidity import LiquidityStatus, LiquidityZone
from app.analysis_engine.liquidity.detector import LiquidityDetector
from app.analysis_engine.liquidity.sweep_detector import SweepDetector
from app.analysis_engine.volatility.analyzer import VolatilityAnalyzer, VolatilityReading
from app.analysis_engine.volatility.compression import CompressionDetector, CompressionReading
from app.analysis_engine.volatility.expansion import ExpansionDetector, ExpansionReading
from app.execution.mt5_executor import MT5Executor


@dataclass
class SymbolState:
    """Everything the manager is currently tracking for one symbol."""

    symbol: str
    zones: list[LiquidityZone] = field(default_factory=list)
    latest_volatility: VolatilityReading | None = None
    latest_compression: CompressionReading | None = None
    latest_expansion: ExpansionReading | None = None
    sweep_events: list[LiquiditySweepEvent] = field(default_factory=list)


class MultiMarketManager:
    """Runs the analysis pipeline (liquidity detection, volatility,
    compression, expansion, sweep detection) across many currency pairs,
    using one shared MT5Executor.

    This is the piece that turns "analyze one symbol" tools into
    "analyze all 10 pairs" — each analyzer stays single-purpose and
    symbol-unaware; this class is what loops them across your watchlist
    and keeps each symbol's state separate.
    """

    def __init__(
        self,
        executor: MT5Executor,
        symbols: list[str],
        timeframe: Timeframe,
        candle_count: int = 200,
        liquidity_detector: LiquidityDetector | None = None,
        volatility_analyzer: VolatilityAnalyzer | None = None,
        compression_detector: CompressionDetector | None = None,
        expansion_detector: ExpansionDetector | None = None,
        sweep_detector: SweepDetector | None = None,
    ) -> None:
        self.executor = executor
        self.symbols = symbols
        self.timeframe = timeframe
        self.candle_count = candle_count

        self.liquidity_detector = liquidity_detector or LiquidityDetector()
        self.volatility_analyzer = volatility_analyzer or VolatilityAnalyzer()
        self.compression_detector = compression_detector or CompressionDetector()
        self.expansion_detector = expansion_detector or ExpansionDetector()
        self.sweep_detector = sweep_detector or SweepDetector()

        self.states: dict[str, SymbolState] = {
            symbol: SymbolState(symbol=symbol) for symbol in symbols
        }

    def refresh_symbol(self, symbol: str) -> SymbolState:
        """Fetches fresh candles for one symbol and re-runs the full
        candle-based pipeline: liquidity zones -> volatility ->
        compression -> expansion -> sweeps."""
        state = self.states[symbol]
        candles = self.executor.fetch_candles(symbol, self.timeframe, self.candle_count)

        if not candles:
            return state

        newly_detected = self.liquidity_detector.detect(candles)
        self._merge_new_zones(state, newly_detected)

        volatility_readings = self.volatility_analyzer.analyze(candles)
        if volatility_readings:
            state.latest_volatility = volatility_readings[-1]

        compression_readings = self.compression_detector.analyze(candles)
        if compression_readings:
            state.latest_compression = compression_readings[-1]

        expansion_readings = self.expansion_detector.analyze(candles)
        if expansion_readings:
            state.latest_expansion = expansion_readings[-1]

        updated_zones, events = self.sweep_detector.detect(state.zones, candles)
        state.zones = updated_zones
        state.sweep_events.extend(events)

        return state

    def refresh_all(self) -> dict[str, SymbolState]:
        """Runs refresh_symbol() across every symbol in the watchlist."""
        for symbol in self.symbols:
            self.refresh_symbol(symbol)
        return self.states

    def process_tick(self, symbol: str) -> SymbolState:
        """Fetches one live tick for a symbol and checks it against that
        symbol's currently tracked zones for a fast, tick-level sweep."""
        state = self.states[symbol]
        tick = self.executor.fetch_tick(symbol)

        updated_zones, events = self.sweep_detector.detect_tick(state.zones, tick)
        state.zones = updated_zones
        state.sweep_events.extend(events)

        return state

    def process_all_ticks(self) -> dict[str, SymbolState]:
        """Runs process_tick() across every symbol in the watchlist. Call
        this in a tight loop for near-real-time sweep detection."""
        for symbol in self.symbols:
            self.process_tick(symbol)
        return self.states

    def _merge_new_zones(
        self, state: SymbolState, newly_detected: list[LiquidityZone]
    ) -> None:
        """Adds newly detected zones only if a similar zone (same type,
        close price) isn't already being tracked for this symbol. This
        avoids re-adding the same swing point every refresh cycle, and
        avoids losing existing zones' swept/invalidated status."""
        tolerance_pct = self.liquidity_detector.equal_level_tolerance_pct

        for zone in newly_detected:
            already_tracked = any(
                existing.liquidity_type == zone.liquidity_type
                and existing.status == LiquidityStatus.ACTIVE
                and abs(existing.price - zone.price) <= existing.price * tolerance_pct
                for existing in state.zones
            )
            if not already_tracked:
                state.zones.append(zone)