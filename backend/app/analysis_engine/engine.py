from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Protocol, Sequence

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.domain.events import LiquiditySweepEvent
from app.analysis_engine.domain.liquidity import LiquidityStatus, LiquidityZone
from app.analysis_engine.liquidity.detector import LiquidityDetector
from app.analysis_engine.liquidity.sweep_detector import SweepDetector
from app.analysis_engine.volatility.analyzer import VolatilityAnalyzer, VolatilityReading
from app.analysis_engine.volatility.compression import CompressionDetector, CompressionReading
from app.analysis_engine.volatility.expansion import ExpansionDetector, ExpansionReading


class ContextBuilder(Protocol):
    """Any future context builder just needs to implement this shape.
    Keeping it as a Protocol (structural typing) instead of importing a
    concrete MarketContextBuilder means engine.py doesn't break while
    context/builder.py doesn't exist yet — and won't need editing once
    it does, as long as build() matches this signature."""

    def build(self, snapshot: "MarketSnapshot") -> object:
        ...


@dataclass(frozen=True)
class MarketSnapshot:
    """The single unified result of running the full analysis pipeline
    on one batch of candles for one symbol. This is what every
    downstream consumer (strategy/entry_engine.py, risk/risk_engine.py,
    the API layer) should read from — none of them need to know that
    five separate detectors ran to produce it.
    """

    symbol: str
    candles_analyzed: int
    zones: list[LiquidityZone]
    sweep_events: list[LiquiditySweepEvent]
    volatility: VolatilityReading | None
    compression: CompressionReading | None
    expansion: ExpansionReading | None
    context: object | None = None  # populated only if a ContextBuilder is supplied


@dataclass
class AnalysisEngine:
    """Orchestrates the full candle-based analysis pipeline for a single
    symbol's candle series:

        1. Detect liquidity zones (swing highs/lows, equal levels)
        2. Merge them with any zones already being tracked from a prior
           run, so existing SWEPT/INVALIDATED status isn't lost and the
           same swing point isn't re-added every call
        3. Check the merged zones against these candles for new sweeps
        4. Run volatility (ATR/regime), compression, and expansion
           analysis over the same candles
        5. Package everything into one MarketSnapshot
        6. If a context_builder was supplied, hand it the snapshot to
           enrich with structural context (trend, key levels, etc.) —
           optional, since context/builder.py doesn't exist yet

    This mirrors what MultiMarketManager already does per-symbol in its
    refresh_symbol() method — the difference is this class is the
    single-symbol, reusable core; MultiMarketManager could eventually
    just loop AnalysisEngine.analyze() across its watchlist instead of
    duplicating the pipeline logic itself.
    """

    liquidity_detector: LiquidityDetector = field(default_factory=LiquidityDetector)
    sweep_detector: SweepDetector = field(default_factory=SweepDetector)
    volatility_analyzer: VolatilityAnalyzer = field(default_factory=VolatilityAnalyzer)
    compression_detector: CompressionDetector = field(default_factory=CompressionDetector)
    expansion_detector: ExpansionDetector = field(default_factory=ExpansionDetector)
    context_builder: ContextBuilder | None = None

    def analyze(
        self,
        candles: Sequence[Candle],
        existing_zones: Sequence[LiquidityZone] | None = None,
    ) -> MarketSnapshot:
        """Runs the full pipeline once over `candles`.

        existing_zones: zones already being tracked for this symbol from
            a previous call (e.g. from SymbolState.zones in
            MultiMarketManager). Pass None on the very first run for a
            symbol. Passing these in lets newly-swept or newly-detected
            zones build on top of history instead of starting blank
            every time.
        """
        if not candles:
            raise ValueError("No market data supplied")

        symbol = candles[-1].symbol

        zones = self._merge_zones(
            existing_zones or [], self.liquidity_detector.detect(candles)
        )

        zones, sweep_events = self.sweep_detector.detect(zones, candles)

        volatility_readings = self.volatility_analyzer.analyze(candles)
        compression_readings = self.compression_detector.analyze(candles)
        expansion_readings = self.expansion_detector.analyze(candles)

        snapshot = MarketSnapshot(
            symbol=symbol,
            candles_analyzed=len(candles),
            zones=zones,
            sweep_events=sweep_events,
            volatility=volatility_readings[-1] if volatility_readings else None,
            compression=compression_readings[-1] if compression_readings else None,
            expansion=expansion_readings[-1] if expansion_readings else None,
        )

        if self.context_builder is not None:
            context = self.context_builder.build(snapshot)
            snapshot = replace(snapshot, context=context)

        return snapshot

    def _merge_zones(
        self,
        existing: Sequence[LiquidityZone],
        newly_detected: Sequence[LiquidityZone],
    ) -> list[LiquidityZone]:
        """Same logic as MultiMarketManager._merge_new_zones: only adds a
        newly detected zone if it isn't already represented in `existing`,
        so status history isn't lost and duplicates aren't created every
        call.

        A newly detected zone is considered a duplicate of an existing one
        (same liquidity_type, same side, price within tolerance) in two
        cases:

        1. `created_at` matches exactly. This means the detector found the
           *same swing point* again — e.g. re-running analyze() over an
           unchanged candle series. It's the identical zone, so it's
           always a duplicate, regardless of whether the existing zone
           has since been swept or invalidated.

        2. `created_at` differs, but the existing zone is still ACTIVE.
           Here the detector found the same level again but anchored to a
           slightly different swing candle (e.g. new candles appended to
           the series) — still fundamentally the same untouched zone
           being re-tracked, so it's treated as a duplicate too.

        If `created_at` differs AND the existing zone is no longer active
        (swept/invalidated), the newly detected zone is treated as a
        genuinely new zone that has formed at a previously-used price
        level, and is kept alongside the old one rather than merged into
        it — the old zone's swept/invalidated history stays intact.
        """
        merged = list(existing)
        tolerance_pct = self.liquidity_detector.equal_level_tolerance_pct

        for zone in newly_detected:
            is_duplicate = False

            for existing_zone in merged:
                if existing_zone.liquidity_type != zone.liquidity_type:
                    continue
                if existing_zone.side != zone.side:
                    continue
                if abs(existing_zone.price - zone.price) > existing_zone.price * tolerance_pct:
                    continue

                if existing_zone.created_at == zone.created_at:
                    is_duplicate = True
                    break
                if existing_zone.status == LiquidityStatus.ACTIVE:
                    is_duplicate = True
                    break
                # existing_zone is swept/invalidated and this is a
                # distinct, later-forming zone at the same level: not a
                # duplicate of this particular existing_zone. Keep
                # checking other existing zones for a real match.

            if not is_duplicate:
                merged.append(zone)

        return merged