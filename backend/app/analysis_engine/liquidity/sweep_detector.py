from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.domain.events import LiquiditySweepEvent
from app.analysis_engine.domain.liquidity import (
    LiquiditySide,
    LiquidityStatus,
    LiquidityZone,
)


@dataclass
class SweepDetector:
    """Scans candles after a zone was created and flags the first candle
    that pierces the zone's level and then closes back on the other side
    (the classic liquidity-grab pattern)."""

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
                )
                return swept_zone, event

        return zone, None

    def _is_sweep(self, zone: LiquidityZone, candle: Candle) -> bool:
        if zone.side == LiquiditySide.BUYSIDE:
            return candle.high >= zone.price and candle.close < zone.price
        else:
            return candle.low <= zone.price and candle.close > zone.price