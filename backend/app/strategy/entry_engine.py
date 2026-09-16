"""
Entry signal generation.

Strategy in plain terms: a liquidity zone (an old swing high/low where
stop orders are likely resting) gets swept — price pokes through it —
and then rejects back the other way. That's the "stop hunt" pattern:
big players run the resting stops, then the real move goes the
opposite direction. This module turns that pattern into a concrete
trade signal.

Direction logic:
  - A BUYSIDE zone (a swing HIGH, where buy-stops rest above price)
    gets swept upward, then price rejects back down -> that's a SELL
    signal (bearish reversal).
  - A SELLSIDE zone (a swing LOW, where sell-stops rest below price)
    gets swept downward, then price rejects back up -> that's a BUY
    signal (bullish reversal).

A signal is only produced when ALL of these are true (hard filters):
  1. A sweep happened (from snapshot.sweep_events).
  2. Price rejected back through the swept level within
     `rejection_confirmation_candles` candles of the sweep.
  3. The broader trend (from StructureAnalyzer) doesn't clearly
     contradict the signal direction — e.g. a SELL signal is blocked
     if the market is in a confirmed BULLISH structure.
  4. The market is currently expanding (ExpansionDetector), in the
     same direction as the signal — confirms the reversal has real
     follow-through instead of being a weak, fading move.

Compression is checked too, but only as a SOFT signal: it's recorded
on the EntrySignal for extra context/confidence, but a signal is never
blocked just because the market wasn't compressed beforehand. Reasoning:
requiring compression before every single sweep would filter out a lot
of otherwise valid setups — sweeps happen without a prior squeeze too.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Sequence

from app.analysis_engine.domain.candle import Candle, Timeframe
from app.analysis_engine.domain.events import LiquiditySweepEvent, SweepDetectionSource
from app.analysis_engine.domain.liquidity import LiquiditySide, LiquidityType
from app.analysis_engine.engine import MarketSnapshot
from app.analysis_engine.structure.analyzer import (
    MarketStructureAnalyzer,
    MarketStructureTrend,
    StructureAnalyzer,
    StructureRegime,
)
from app.analysis_engine.volatility.compression import CompressionDetector
from app.analysis_engine.volatility.expansion import ExpansionDirection
from app.core.settings import get_settings


class TradeDirection(str, Enum):
    """Which way the resulting trade would go. Deliberately separate
    from LiquiditySide (BUYSIDE/SELLSIDE), which describes the zone
    that got swept, not the trade direction — sweeping a BUYSIDE zone
    actually produces a SELL trade, not a BUY, so conflating the two
    would be confusing."""

    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class EntrySignal:
    """A single actionable entry opportunity."""

    symbol: str
    timeframe: Timeframe
    direction: TradeDirection
    signal_time: datetime  # timestamp of the candle that confirmed rejection
    entry_price: float  # close of the confirmation candle
    stop_loss: float  # placed beyond the sweep's extreme price, with a buffer
    zone_id: str
    liquidity_type: LiquidityType
    level_price: float  # the swept zone's price level
    sweep_price: float  # how far price ran during the sweep
    trend: MarketStructureTrend
    expansion_confirmed: bool
    compression_confirmed: bool  # soft signal only — never gates the trade
    htf_trend: MarketStructureTrend | None = None


class EntryEngine:
    """
    Scans a MarketSnapshot for sweep events and turns qualifying ones
    into EntrySignals. Supports multi-timeframe analysis against HTF (e.g. H1)
    market structure and liquidity.

    rejection_confirmation_candles: how many candles after the sweep
        to look for a close back through the level before giving up on
        that sweep as a valid setup.
    stop_buffer_pct: extra room placed beyond the sweep's extreme price
        for the stop loss, as a fraction of price (e.g. 0.0005 = 0.05%),
        so the stop isn't sitting exactly on a level that's likely to
        get re-tested.
    allow_ranging_trend: if True, RANGING structure doesn't block a
        signal in either direction (only a clearly opposing trend
        does). If False, only a matching trend (BULLISH for BUY,
        BEARISH for SELL) is allowed through.
    require_expansion: if True, requires directional expansion momentum.
    require_htf_alignment: if True and htf_candles/htf_snapshot are provided,
        enforces higher-timeframe confluence.
    min_rejection_wick_pct: minimum wick size as fraction of total candle range
        for strong rejection confirmation (e.g. 0.50 = 50%).
    rejection_close_range_pct: candle close must be within this fraction of total
        range opposite to sweep direction (e.g. 0.35 = outer 35%).
    min_volume_multiplier: rejection candle volume must exceed rolling average
        by this factor (e.g. 1.2 = 120%), skipped if volume is unpopulated.
    volume_ma_period: rolling candle count for volume average.
    require_trend_alignment: if True, only setups aligned with structure trend
        are allowed through.
    require_recent_compression: if True, requires market to have compressed
        prior to the sweep.
    compression_lookback_candles: how many candles prior to sweep to inspect
        for compression.
    expansion_threshold: minimum expansion ratio required if expansion is enforced.
    """

    def __init__(
        self,
        structure_analyzer: StructureAnalyzer | None = None,
        require_rejection_confirmation: bool | None = None,
        rejection_confirmation_candles: int | None = None,
        stop_buffer_pct: float | None = None,
        allow_ranging_trend: bool | None = None,
        require_expansion: bool | None = None,
        require_htf_alignment: bool | None = None,
        min_penetration_ticks: int | None = None,
        require_stay_beyond: bool | None = None,
        min_rejection_wick_pct: float | None = None,
        rejection_close_range_pct: float | None = None,
        min_volume_multiplier: float | None = None,
        volume_ma_period: int | None = None,
        require_trend_alignment: bool | None = None,
        require_recent_compression: bool | None = None,
        compression_lookback_candles: int | None = None,
        expansion_threshold: float | None = None,
        compression_detector: CompressionDetector | None = None,
        enable_session_filter: bool | None = None,
        session_start_hour_utc: int | None = None,
        session_end_hour_utc: int | None = None,
        max_stop_loss_pips: float | None = None,
        htf_alignment_symbols: list[str] | None = None,
    ) -> None:
        settings = get_settings().analysis

        self.htf_alignment_symbols = (
            [s.upper() for s in htf_alignment_symbols] if htf_alignment_symbols is not None else None
        )
        self.require_rejection_confirmation = (
            require_rejection_confirmation
            if require_rejection_confirmation is not None
            else getattr(settings, "require_rejection_confirmation", False)
        )
        self.rejection_confirmation_candles = (
            rejection_confirmation_candles
            if rejection_confirmation_candles is not None
            else getattr(settings, "rejection_confirmation_candles", 3)
        )
        self.stop_buffer_pct = (
            stop_buffer_pct
            if stop_buffer_pct is not None
            else getattr(settings, "stop_buffer_pct", 0.0005)
        )
        self.allow_ranging_trend = (
            allow_ranging_trend
            if allow_ranging_trend is not None
            else getattr(settings, "allow_ranging_trend", True)
        )
        self.require_expansion = (
            require_expansion
            if require_expansion is not None
            else getattr(settings, "require_expansion", False)
        )
        self.require_htf_alignment = (
            require_htf_alignment
            if require_htf_alignment is not None
            else getattr(settings, "require_htf_alignment", False)
        )
        self.min_penetration_ticks = (
            min_penetration_ticks
            if min_penetration_ticks is not None
            else getattr(settings, "min_penetration_ticks", 0)
        )
        self.require_stay_beyond = (
            require_stay_beyond
            if require_stay_beyond is not None
            else getattr(settings, "require_stay_beyond", False)
        )
        self.min_rejection_wick_pct = (
            min_rejection_wick_pct
            if min_rejection_wick_pct is not None
            else getattr(settings, "min_rejection_wick_pct", 0.40)
        )
        self.rejection_close_range_pct = (
            rejection_close_range_pct
            if rejection_close_range_pct is not None
            else getattr(settings, "rejection_close_range_pct", 0.50)
        )
        self.min_volume_multiplier = (
            min_volume_multiplier
            if min_volume_multiplier is not None
            else getattr(settings, "min_volume_multiplier", 0.0)
        )
        self.volume_ma_period = (
            volume_ma_period
            if volume_ma_period is not None
            else getattr(settings, "volume_ma_period", 20)
        )
        self.require_trend_alignment = (
            require_trend_alignment
            if require_trend_alignment is not None
            else getattr(settings, "require_trend_alignment", True)
        )
        self.require_recent_compression = (
            require_recent_compression
            if require_recent_compression is not None
            else getattr(settings, "require_recent_compression", False)
        )
        self.compression_lookback_candles = (
            compression_lookback_candles
            if compression_lookback_candles is not None
            else getattr(settings, "compression_lookback_candles", 6)
        )
        self.expansion_threshold = (
            expansion_threshold
            if expansion_threshold is not None
            else getattr(settings, "expansion_threshold", 1.5)
        )
        self.enable_session_filter = (
            enable_session_filter
            if enable_session_filter is not None
            else getattr(settings, "enable_session_filter", True)
        )
        self.session_start_hour_utc = (
            session_start_hour_utc
            if session_start_hour_utc is not None
            else getattr(settings, "session_start_hour_utc", 7)
        )
        self.session_end_hour_utc = (
            session_end_hour_utc
            if session_end_hour_utc is not None
            else getattr(settings, "session_end_hour_utc", 18)
        )
        self.max_stop_loss_pips = (
            max_stop_loss_pips
            if max_stop_loss_pips is not None
            else getattr(settings, "max_stop_loss_pips", 18.0)
        )

        if self.rejection_confirmation_candles < 0:
            raise ValueError("rejection_confirmation_candles must be >= 0")
        if self.stop_buffer_pct < 0:
            raise ValueError("stop_buffer_pct must be >= 0")
        if not (0 <= self.min_rejection_wick_pct <= 1):
            raise ValueError("min_rejection_wick_pct must be between 0 and 1")
        if not (0 <= self.rejection_close_range_pct <= 1):
            raise ValueError("rejection_close_range_pct must be between 0 and 1")
        if self.volume_ma_period < 1:
            raise ValueError("volume_ma_period must be >= 1")
        if self.compression_lookback_candles < 1:
            raise ValueError("compression_lookback_candles must be >= 1")

        self.structure_analyzer = structure_analyzer or StructureAnalyzer()
        self.compression_detector = compression_detector or CompressionDetector()

    def evaluate(
        self,
        snapshot: MarketSnapshot,
        candles: Sequence[Candle],
        htf_snapshot: MarketSnapshot | None = None,
        htf_candles: Sequence[Candle] | None = None,
        require_htf_alignment: bool | None = None,
    ) -> list[EntrySignal]:
        """Checks every sweep event in `snapshot` and returns an
        EntrySignal for each one that passes all hard filters, including
        multi-timeframe market structure confluence if `htf_candles` are provided."""
        if not candles:
            return []

        trend = self.structure_analyzer.current_trend(candles)
        htf_trend: MarketStructureTrend | None = None
        if htf_candles and len(htf_candles) >= 10:
            htf_trend = self.structure_analyzer.current_trend(htf_candles)

        signals: list[EntrySignal] = []

        for event in snapshot.sweep_events:
            direction = self._implied_direction(event.side)

            # Minimum penetration check (meaningful break past level in ticks)
            if self.min_penetration_ticks > 0:
                pip_size = 0.01 if "JPY" in event.symbol.upper() else 0.0001
                point_size = pip_size / 10.0
                min_pen_dist = self.min_penetration_ticks * point_size
                penetration = abs(event.sweep_price - event.level_price)
                if penetration < min_pen_dist:
                    continue

            if not self._trend_allows(direction, trend):
                continue

            # Multi-timeframe confluence check
            # Live structure classification against H1 determines whether H1 alignment is required:
            # If H1 structure is TRENDING, H1 alignment is enforced.
            # If H1 structure is RANGING, H1 alignment is relaxed/skipped.
            if require_htf_alignment is False:
                enforce_htf = False
            elif require_htf_alignment is True:
                enforce_htf = True
            elif self.htf_alignment_symbols is not None:
                symbol_in_list = event.symbol.upper() in self.htf_alignment_symbols
                enforce_htf = self.require_htf_alignment and symbol_in_list
            else:
                enforce_htf = self.require_htf_alignment

            if enforce_htf and htf_trend is not None:
                if not self._htf_alignment_allows(direction, htf_trend, htf_snapshot):
                    continue

            # Stay beyond verification (filtering out single-wick touch-and-go spikes)
            if self.require_stay_beyond and not self._verify_stay_beyond(event, candles):
                continue

            if self.require_rejection_confirmation:
                confirmation_candle = self._find_rejection_candle(
                    event.occurred_at, event.level_price, direction, candles
                )
                if confirmation_candle is None:
                    continue
            else:
                confirmation_candle = self._find_sweep_candle(event.occurred_at, candles)
                if confirmation_candle is None:
                    continue

            # Session / Killzone Filter: Avoid Asian and rollover low-volume dead zones (21:00 - 06:45 UTC)
            if self.enable_session_filter and confirmation_candle:
                ts = confirmation_candle.timestamp
                ts_utc = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
                if ts_utc.hour < self.session_start_hour_utc or ts_utc.hour >= self.session_end_hour_utc:
                    continue

            expansion_confirmed = self._expansion_confirms(direction, snapshot)
            if self.require_expansion and not expansion_confirmed:
                continue

            compression_confirmed = self._has_recent_compression(
                snapshot, candles, event.occurred_at
            )
            if self.require_recent_compression and not compression_confirmed:
                continue

            stop_loss = self._compute_stop_loss(direction, event.sweep_price)

            # Max stop loss filter: reject setups where risk exceeds max_stop_loss_pips
            if self.max_stop_loss_pips is not None and self.max_stop_loss_pips > 0:
                pip_size = 0.01 if "JPY" in event.symbol.upper() else 0.0001
                risk_pips = abs(confirmation_candle.close - stop_loss) / pip_size
                if risk_pips > self.max_stop_loss_pips:
                    continue

            signals.append(
                EntrySignal(
                    symbol=event.symbol,
                    timeframe=event.timeframe,
                    direction=direction,
                    signal_time=confirmation_candle.timestamp,
                    entry_price=confirmation_candle.close,
                    stop_loss=stop_loss,
                    zone_id=event.zone_id,
                    liquidity_type=event.liquidity_type,
                    level_price=event.level_price,
                    sweep_price=event.sweep_price,
                    trend=trend,
                    expansion_confirmed=expansion_confirmed,
                    compression_confirmed=compression_confirmed,
                    htf_trend=htf_trend,
                )
            )

        return signals

    def _implied_direction(self, swept_side: LiquiditySide) -> TradeDirection:
        # Sweeping a BUYSIDE (high) zone implies a SELL reversal;
        # sweeping a SELLSIDE (low) zone implies a BUY reversal.
        return (
            TradeDirection.SELL
            if swept_side == LiquiditySide.BUYSIDE
            else TradeDirection.BUY
        )

    def _trend_allows(self, direction: TradeDirection, trend: MarketStructureTrend) -> bool:
        if not self.require_trend_alignment:
            return True

        if trend == MarketStructureTrend.RANGING:
            return self.allow_ranging_trend

        if direction == TradeDirection.BUY:
            return trend == MarketStructureTrend.BULLISH
        return trend == MarketStructureTrend.BEARISH

    def is_htf_alignment_required(self, htf_candles: Sequence[Candle] | None = None) -> bool:
        """
        Determines whether H1 alignment is required based on live structure classification.
        Returns True if H1 structure is TRENDING; returns False if RANGING or not enough data.
        """
        if not self.require_htf_alignment:
            return False
        if not htf_candles or len(htf_candles) < 10:
            return False
        if hasattr(self.structure_analyzer, "classify_regime"):
            return self.structure_analyzer.classify_regime(htf_candles) == StructureRegime.TRENDING
        return False

    def _htf_alignment_allows(
        self,
        direction: TradeDirection,
        htf_trend: MarketStructureTrend,
        htf_snapshot: MarketSnapshot | None = None,
    ) -> bool:
        """
        Validates whether higher-timeframe (H1) structure permits an execution (M15) trade:
        - If HTF trend directly agrees (BULLISH for BUY, BEARISH for SELL), trade is allowed.
        - If HTF trend is RANGING and allow_ranging_trend is True, trade is allowed.
        - If HTF trend opposes (BEARISH for BUY, BULLISH for SELL):
          Trade is BLOCKED unless HTF itself recently swept opposing liquidity
          (e.g., H1 swept SELLSIDE liquidity -> macro discount reversal point).
        """
        if self._trend_allows(direction, htf_trend):
            return True

        if htf_snapshot and htf_snapshot.sweep_events:
            if direction == TradeDirection.BUY:
                for ev in htf_snapshot.sweep_events:
                    if ev.side == LiquiditySide.SELLSIDE:
                        return True
            elif direction == TradeDirection.SELL:
                for ev in htf_snapshot.sweep_events:
                    if ev.side == LiquiditySide.BUYSIDE:
                        return True

        return False

    def _verify_stay_beyond(self, event: LiquiditySweepEvent, candles: Sequence[Candle]) -> bool:
        """
        Verifies that price actually stayed beyond the level for a bit,
        filtering out instantaneous touch-and-go wicks.
        """
        if event.detected_via == SweepDetectionSource.TICK:
            return True

        sweep_idx = None
        for i, c in enumerate(candles):
            if c.timestamp == event.occurred_at:
                sweep_idx = i
                break
            if c.timestamp <= event.occurred_at:
                sweep_idx = i

        if sweep_idx is None:
            return True

        sweep_candle = candles[sweep_idx]

        # If the sweep candle closed beyond the level, it sustained presence for the candle
        if event.side == LiquiditySide.BUYSIDE:
            if sweep_candle.close >= event.level_price:
                return True
            # Or if subsequent candle traded beyond the level
            if sweep_idx + 1 < len(candles) and candles[sweep_idx + 1].high >= event.level_price:
                return True
        else:
            if sweep_candle.close <= event.level_price:
                return True
            if sweep_idx + 1 < len(candles) and candles[sweep_idx + 1].low <= event.level_price:
                return True

        return False

    def _has_recent_compression(
        self,
        snapshot: MarketSnapshot,
        candles: Sequence[Candle],
        sweep_time: datetime | None = None,
    ) -> bool:
        """
        Checks if the market was recently compressed either via snapshot.compression
        or by analyzing historical compression within compression_lookback_candles.
        """
        if snapshot.compression is not None and snapshot.compression.is_compressed:
            return True

        if not candles:
            return False

        try:
            readings = self.compression_detector.analyze(candles)
            if not readings:
                return False

            sweep_idx = len(candles) - 1
            if sweep_time is not None:
                for idx, c in enumerate(candles):
                    if c.timestamp == sweep_time:
                        sweep_idx = idx
                        break
                    if c.timestamp <= sweep_time:
                        sweep_idx = idx

            start_idx = max(0, sweep_idx - self.compression_lookback_candles)
            end_idx = min(len(candles) - 1, sweep_idx + 1)
            target_timestamps = {c.timestamp for c in candles[start_idx : end_idx + 1]}

            for reading in readings:
                if reading.timestamp in target_timestamps and reading.is_compressed:
                    return True
        except Exception:
            pass

        return False

    def _is_strong_rejection(
        self,
        candle: Candle,
        sweep_level: float,
        sweep_side: LiquiditySide | TradeDirection,
        candles: Sequence[Candle] | None = None,
        candle_idx: int | None = None,
    ) -> bool:
        """
        Validates whether a candle qualifies as a strong rejection of a swept liquidity level:
        1. Closes back across the level (reversal direction).
        2. Rejection wick >= min_rejection_wick_pct of total candle range.
        3. Close in outer portion (rejection_close_range_pct) of its own range opposite to sweep.
        4. Volume >= min_volume_multiplier of rolling average if volume data is present.
        """
        total_range = candle.high - candle.low
        if total_range <= 0:
            return False

        side_val = sweep_side.value if hasattr(sweep_side, "value") else str(sweep_side)
        is_bullish = side_val.lower() in ("sellside", "sell_side", "buy")
        is_bearish = side_val.lower() in ("buyside", "buy_side", "sell")

        if not is_bullish and not is_bearish:
            return False

        if is_bullish:
            # Swept low downward, price rejected upward:
            # Must close back above the swept level
            if candle.close <= sweep_level:
                return False

            # Lower wick must be >= min_rejection_wick_pct of total range
            lower_wick = min(candle.open, candle.close) - candle.low
            if lower_wick / total_range < self.min_rejection_wick_pct:
                return False

            # Close must be in the upper portion of range (e.g. top 35%)
            if (candle.high - candle.close) / total_range > self.rejection_close_range_pct:
                return False

        else:
            # Swept high upward, price rejected downward:
            # Must close back below the swept level
            if candle.close >= sweep_level:
                return False

            # Upper wick must be >= min_rejection_wick_pct of total range
            upper_wick = candle.high - max(candle.open, candle.close)
            if upper_wick / total_range < self.min_rejection_wick_pct:
                return False

            # Close must be in the lower portion of range (e.g. bottom 35%)
            if (candle.close - candle.low) / total_range > self.rejection_close_range_pct:
                return False

        # Volume confirmation check (skipped if candle has no volume or multiplier <= 0)
        if candle.volume is not None and self.min_volume_multiplier > 0 and candles:
            idx = candle_idx
            if idx is None:
                for i, c in enumerate(candles):
                    if c.timestamp == candle.timestamp:
                        idx = i
                        break

            if idx is not None and idx > 0:
                start_vol_idx = max(0, idx - self.volume_ma_period)
                prior_vols = [
                    c.volume
                    for c in candles[start_vol_idx:idx]
                    if c.volume is not None and c.volume > 0
                ]
                if prior_vols:
                    avg_vol = sum(prior_vols) / len(prior_vols)
                    if avg_vol > 0 and candle.volume < avg_vol * self.min_volume_multiplier:
                        return False

        return True

    def _find_rejection_candle(
        self,
        swept_at: datetime,
        level_price: float,
        direction: TradeDirection,
        candles: Sequence[Candle],
    ) -> Candle | None:
        """Looks for the sweep candle itself, then up to
        `rejection_confirmation_candles` candles after it, for the
        first candle that qualifies as a strong rejection."""
        start_index = None
        for i, candle in enumerate(candles):
            if candle.timestamp == swept_at:
                start_index = i
                break
            # detected_via can be TICK, whose occurred_at may not match
            # any candle's timestamp exactly — fall back to the last
            # candle at or before the sweep time.
            if candle.timestamp <= swept_at:
                start_index = i

        if start_index is None:
            return None

        end_index = min(start_index + self.rejection_confirmation_candles, len(candles) - 1)
        sweep_side = (
            LiquiditySide.SELLSIDE
            if direction == TradeDirection.BUY
            else LiquiditySide.BUYSIDE
        )

        for i in range(start_index, end_index + 1):
            candle = candles[i]
            if self._is_strong_rejection(
                candle=candle,
                sweep_level=level_price,
                sweep_side=sweep_side,
                candles=candles,
                candle_idx=i,
            ):
                return candle

        return None

    def _find_sweep_candle(
        self,
        swept_at: datetime,
        candles: Sequence[Candle],
    ) -> Candle | None:
        """Finds the candle corresponding to the sweep event or the closest candle at/before it."""
        if not candles:
            return None
        for candle in candles:
            if candle.timestamp == swept_at:
                return candle
        last_at_or_before = None
        for candle in candles:
            if candle.timestamp <= swept_at:
                last_at_or_before = candle
            else:
                break
        if last_at_or_before is not None:
            return last_at_or_before
        return candles[-1]

    def _expansion_confirms(self, direction: TradeDirection, snapshot: MarketSnapshot) -> bool:
        if snapshot.expansion is None or not snapshot.expansion.is_expanding:
            return False

        if self.expansion_threshold is not None and hasattr(snapshot.expansion, "expansion_ratio"):
            if (
                snapshot.expansion.expansion_ratio is not None
                and snapshot.expansion.expansion_ratio < self.expansion_threshold
            ):
                return False

        if direction == TradeDirection.BUY:
            return snapshot.expansion.direction == ExpansionDirection.BULLISH
        return snapshot.expansion.direction == ExpansionDirection.BEARISH

    def _compute_stop_loss(self, direction: TradeDirection, sweep_price: float) -> float:
        if direction == TradeDirection.BUY:
            # sweep ran price down through a low; stop goes further
            # below that extreme, not right at it.
            return sweep_price * (1 - self.stop_buffer_pct)
        # sweep ran price up through a high; stop goes further above.
        return sweep_price * (1 + self.stop_buffer_pct)