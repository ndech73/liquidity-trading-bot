from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.domain.events import LiquiditySweepEvent, SweepDetectionSource
from app.analysis_engine.domain.liquidity import (
    LiquiditySide,
    LiquidityStatus,
    LiquidityZone,
)
from app.analysis_engine.domain.tick import Tick


@dataclass
class SweepDetector:
    """Detects when a LiquidityZone gets swept, via two paths:

    - detect(): scans closed candles for genuine liquidity sweeps. Price must
      break the level by at least `min_penetration` / `min_penetration_ticks` AND
      stay beyond it for at least `min_hold_candles` before closing back across
      the level on the rejection. This filters out fake liquidity grabs and single-wick
      spikes.
    - detect_tick(): watches live ticks and confirms a sweep only once
      price has crossed the level by at least `min_penetration` / `min_penetration_ticks`
      AND stayed beyond it for at least `min_hold_seconds`.

    min_penetration: how far past the level (in price units, same scale
        as zone.price) price must travel before it counts.
    min_penetration_ticks: how far past the level in ticks/points (e.g. 20 ticks = 2.0 pips)
        price must travel before it counts.
    min_hold_seconds: how long price must stay beyond the level,
        continuously, before it counts (for ticks).
    min_hold_candles: how many candles price must stay beyond the level
        before rejecting back (for candles). Default 0 allows single-candle wicks if
        sufficient penetration, >= 1 requires price to actually hold beyond.
    """

    min_penetration: float = 0.0
    min_penetration_ticks: int = 0
    min_hold_seconds: float = 0.0
    min_hold_candles: int = 0
    min_penetration_atr_ratio: float | None = None
    min_penetration_pips_floor: float | None = None
    _pending: dict[str, tuple[datetime, float]] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        try:
            from app.core.settings import get_settings
            cfg = get_settings().analysis
            if self.min_penetration_atr_ratio is None:
                self.min_penetration_atr_ratio = cfg.min_penetration_atr_ratio
            if self.min_penetration_pips_floor is None:
                self.min_penetration_pips_floor = cfg.min_penetration_pips_floor
        except Exception:
            pass
        if self.min_penetration_atr_ratio is None:
            self.min_penetration_atr_ratio = 0.10
        if self.min_penetration_pips_floor is None:
            self.min_penetration_pips_floor = 2.0

    @staticmethod
    def _compute_atr_from_candles(candles: Sequence[Candle], period: int = 14) -> float:
        if not candles:
            return 0.0
        if len(candles) == 1:
            return candles[0].high - candles[0].low

        true_ranges = [candles[0].high - candles[0].low]
        for i in range(1, len(candles)):
            c = candles[i]
            prev_c = candles[i - 1]
            tr = max(
                c.high - c.low,
                abs(c.high - prev_c.close),
                abs(c.low - prev_c.close),
            )
            true_ranges.append(tr)

        lookback = min(period, len(true_ranges))
        return sum(true_ranges[-lookback:]) / lookback

    def _effective_min_penetration(
        self, zone: LiquidityZone, current_atr: float | None = None
    ) -> float:
        symbol_upper = zone.symbol.upper()
        pip_size = 0.01 if "JPY" in symbol_upper else 0.0001
        point_size = pip_size / 10.0

        ratio = self.min_penetration_atr_ratio if self.min_penetration_atr_ratio is not None else 0.10
        floor_pips = self.min_penetration_pips_floor if self.min_penetration_pips_floor is not None else 2.0

        floor_penetration = floor_pips * pip_size

        atr_penetration = 0.0
        if current_atr is not None and current_atr > 0:
            atr_penetration = current_atr * ratio

        # Required penetration is ATR-scaled with a hard floor in price units
        required = max(floor_penetration, atr_penetration)

        # Also respect explicit min_penetration or min_penetration_ticks if set higher
        if self.min_penetration > 0:
            required = max(required, self.min_penetration)
        if self.min_penetration_ticks > 0:
            required = max(required, self.min_penetration_ticks * point_size)

        return required

    def detect(
        self,
        zones: Sequence[LiquidityZone],
        candles: Sequence[Candle],
        current_atr: float | None = None,
    ) -> tuple[list[LiquidityZone], list[LiquiditySweepEvent]]:
        if current_atr is None and candles:
            current_atr = self._compute_atr_from_candles(candles)

        updated_zones: list[LiquidityZone] = []
        events: list[LiquiditySweepEvent] = []

        for zone in zones:
            if zone.status != LiquidityStatus.ACTIVE:
                updated_zones.append(zone)
                continue

            swept_zone, event = self._check_zone(zone, candles, current_atr=current_atr)
            updated_zones.append(swept_zone)
            if event is not None:
                events.append(event)

        return updated_zones, events

    def detect_tick(
        self,
        zones: Sequence[LiquidityZone],
        tick: Tick,
        current_atr: float | None = None,
    ) -> tuple[list[LiquidityZone], list[LiquiditySweepEvent]]:
        """Checks a single live tick against all active zones for the same
        symbol. Call this on every incoming tick from the feed."""
        updated_zones: list[LiquidityZone] = []
        events: list[LiquiditySweepEvent] = []

        for zone in zones:
            if (
                zone.status != LiquidityStatus.ACTIVE
                or zone.symbol != tick.symbol
                or tick.timestamp <= zone.created_at
            ):
                updated_zones.append(zone)
                continue

            min_pen = self._effective_min_penetration(zone, current_atr=current_atr)
            penetration = self._penetration(zone, tick)

            if penetration < 0:
                # Price is back on the safe side of the level — any
                # in-progress crossing is invalidated, forget it.
                self._pending.pop(zone.id, None)
                updated_zones.append(zone)
                continue

            first_seen = self._pending.get(zone.id)
            if first_seen is None:
                # First tick to cross the level. Start the clock, but
                # don't fire yet unless both filters are already
                # satisfied by this single tick (e.g. filters set to 0).
                self._pending[zone.id] = (tick.timestamp, penetration)
                first_crossed_at, best_penetration = tick.timestamp, penetration
            else:
                first_crossed_at, prior_penetration = first_seen
                best_penetration = max(prior_penetration, penetration)
                self._pending[zone.id] = (first_crossed_at, best_penetration)

            held_seconds = (tick.timestamp - first_crossed_at).total_seconds()
            _EPSILON = 1e-9
            if (
                best_penetration >= (min_pen - _EPSILON)
                and held_seconds >= self.min_hold_seconds
            ):
                sweep_price = tick.ask if zone.side == LiquiditySide.BUYSIDE else tick.bid
                swept_zone = zone.mark_swept(at=first_crossed_at, sweep_price=sweep_price)
                event = LiquiditySweepEvent(
                    symbol=zone.symbol,
                    timeframe=zone.timeframe,
                    occurred_at=first_crossed_at,
                    zone_id=zone.id,
                    side=zone.side,
                    liquidity_type=zone.liquidity_type,
                    level_price=zone.price,
                    sweep_price=sweep_price,
                    detected_via=SweepDetectionSource.TICK,
                )
                self._pending.pop(zone.id, None)
                updated_zones.append(swept_zone)
                events.append(event)
            else:
                updated_zones.append(zone)

        return updated_zones, events

    def _penetration(self, zone: LiquidityZone, tick: Tick) -> float:
        """How far past the level this tick is. Positive means price is
        beyond the level (on the sweep side); negative means it hasn't
        reached it or has retreated back."""
        if zone.side == LiquiditySide.BUYSIDE:
            return tick.ask - zone.price
        else:
            return zone.price - tick.bid

    def _check_zone(
        self,
        zone: LiquidityZone,
        candles: Sequence[Candle],
        current_atr: float | None = None,
    ) -> tuple[LiquidityZone, LiquiditySweepEvent | None]:
        min_pen = self._effective_min_penetration(zone, current_atr=current_atr)

        crossing_active = False
        crossing_started: datetime | None = None
        best_sweep_price: float | None = None
        candles_held = 0

        for candle in candles:
            if candle.timestamp <= zone.created_at:
                continue

            _EPSILON = 1e-9
            if zone.side == LiquiditySide.BUYSIDE:
                penetrates = candle.high >= (zone.price + min_pen - _EPSILON)
                holds_beyond = candle.close >= zone.price
                rejection = candle.close < zone.price

                if not crossing_active:
                    if penetrates:
                        if holds_beyond:
                            crossing_active = True
                            crossing_started = candle.timestamp
                            best_sweep_price = candle.high
                            candles_held = 1
                        elif rejection and self.min_hold_candles == 0:
                            sweep_price = candle.high
                            swept_zone = zone.mark_swept(at=candle.timestamp, sweep_price=sweep_price)
                            event = LiquiditySweepEvent(
                                symbol=zone.symbol,
                                timeframe=zone.timeframe,
                                occurred_at=candle.timestamp,
                                zone_id=zone.id,
                                side=zone.side,
                                liquidity_type=zone.liquidity_type,
                                level_price=zone.price,
                                sweep_price=sweep_price,
                                detected_via=SweepDetectionSource.CANDLE,
                            )
                            return swept_zone, event
                else:
                    best_sweep_price = max(best_sweep_price or candle.high, candle.high)
                    if holds_beyond:
                        candles_held += 1
                    elif rejection:
                        if candles_held >= self.min_hold_candles and (best_sweep_price - zone.price) >= (min_pen - _EPSILON):
                            swept_zone = zone.mark_swept(at=crossing_started or candle.timestamp, sweep_price=best_sweep_price)
                            event = LiquiditySweepEvent(
                                symbol=zone.symbol,
                                timeframe=zone.timeframe,
                                occurred_at=candle.timestamp,
                                zone_id=zone.id,
                                side=zone.side,
                                liquidity_type=zone.liquidity_type,
                                level_price=zone.price,
                                sweep_price=best_sweep_price,
                                detected_via=SweepDetectionSource.CANDLE,
                            )
                            return swept_zone, event
                        crossing_active = False
                        candles_held = 0
            else:
                # SELLSIDE zone
                penetrates = candle.low <= (zone.price - min_pen + _EPSILON)
                holds_beyond = candle.close <= zone.price
                rejection = candle.close > zone.price

                if not crossing_active:
                    if penetrates:
                        if holds_beyond:
                            crossing_active = True
                            crossing_started = candle.timestamp
                            best_sweep_price = candle.low
                            candles_held = 1
                        elif rejection and self.min_hold_candles == 0:
                            sweep_price = candle.low
                            swept_zone = zone.mark_swept(at=candle.timestamp, sweep_price=sweep_price)
                            event = LiquiditySweepEvent(
                                symbol=zone.symbol,
                                timeframe=zone.timeframe,
                                occurred_at=candle.timestamp,
                                zone_id=zone.id,
                                side=zone.side,
                                liquidity_type=zone.liquidity_type,
                                level_price=zone.price,
                                sweep_price=sweep_price,
                                detected_via=SweepDetectionSource.CANDLE,
                            )
                            return swept_zone, event
                else:
                    best_sweep_price = min(best_sweep_price or candle.low, candle.low)
                    if holds_beyond:
                        candles_held += 1
                    elif rejection:
                        if candles_held >= self.min_hold_candles and (zone.price - best_sweep_price) >= (min_pen - _EPSILON):
                            swept_zone = zone.mark_swept(at=crossing_started or candle.timestamp, sweep_price=best_sweep_price)
                            event = LiquiditySweepEvent(
                                symbol=zone.symbol,
                                timeframe=zone.timeframe,
                                occurred_at=candle.timestamp,
                                zone_id=zone.id,
                                side=zone.side,
                                liquidity_type=zone.liquidity_type,
                                level_price=zone.price,
                                sweep_price=best_sweep_price,
                                detected_via=SweepDetectionSource.CANDLE,
                            )
                            return swept_zone, event
                        crossing_active = False
                        candles_held = 0

        return zone, None

    def _is_sweep(
        self,
        zone: LiquidityZone,
        candle: Candle,
        current_atr: float | None = None,
    ) -> bool:
        min_pen = self._effective_min_penetration(zone, current_atr=current_atr)
        _EPSILON = 1e-9
        if zone.side == LiquiditySide.BUYSIDE:
            return candle.high >= (zone.price + min_pen - _EPSILON) and candle.close < zone.price
        else:
            return candle.low <= (zone.price - min_pen + _EPSILON) and candle.close > zone.price