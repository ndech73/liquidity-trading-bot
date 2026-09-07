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

    - detect(): scans closed candles for the classic pattern (wick pierces
      the level, candle closes back on the other side).
    - detect_tick(): watches live ticks and confirms a sweep only once
      price has crossed the level by at least `min_penetration` AND
      stayed beyond it for at least `min_hold_seconds`. This filters out
      single-tick spikes that touch and instantly reverse — those are
      treated as noise, not real sweeps.

    min_penetration: how far past the level (in price units, same scale
        as zone.price — e.g. 0.0001 for a 1-pip filter on EURUSD) price
        must travel before it counts.
    min_hold_seconds: how long price must stay beyond the level,
        continuously, before it counts. 0 for either parameter disables
        that check.
    """

    min_penetration: float = 0.0
    min_hold_seconds: float = 0.0
    _pending: dict[str, tuple[datetime, float]] = field(
        default_factory=dict, init=False, repr=False
    )

    def detect(
        self,
        zones: Sequence[LiquidityZone],
        candles: Sequence[Candle],
    ) -> tuple[list[LiquidityZone], list[LiquiditySweepEvent]]:
        updated_zones: list[LiquidityZone] = []
        events: list[LiquiditySweepEvent] = []

        for zone in zones:
            if zone.status != LiquidityStatus.ACTIVE:
                updated_zones.append(zone)
                continue

            swept_zone, event = self._check_zone(zone, candles)
            updated_zones.append(swept_zone)
            if event is not None:
                events.append(event)

        return updated_zones, events

    def detect_tick(
        self,
        zones: Sequence[LiquidityZone],
        tick: Tick,
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

            if (
                best_penetration >= self.min_penetration
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
        self, zone: LiquidityZone, candles: Sequence[Candle]
    ) -> tuple[LiquidityZone, LiquiditySweepEvent | None]:
        for candle in candles:
            if candle.timestamp <= zone.created_at:
                continue

            if self._is_sweep(zone, candle):
                sweep_price = (
                    candle.high if zone.side == LiquiditySide.BUYSIDE else candle.low
                )
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

        return zone, None

    def _is_sweep(self, zone: LiquidityZone, candle: Candle) -> bool:
        if zone.side == LiquiditySide.BUYSIDE:
            return candle.high >= zone.price and candle.close < zone.price
        else:
            return candle.low <= zone.price and candle.close > zone.price