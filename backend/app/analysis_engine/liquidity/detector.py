from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from app.analysis_engine.domain.candle import Candle
from app.analysis_engine.domain.liquidity import (
    LiquiditySide,
    LiquidityType,
    LiquidityZone,
)


@dataclass
class LiquidityDetector:
    """Scans a candle series for swing highs/lows, then groups nearby
    swing points into equal-highs / equal-lows zones.

    lookback: how many candles on each side must be lower (for a high) or
        higher (for a low) for the middle candle to count as a swing point.
    equal_level_tolerance_pct: how close two swing prices must be, as a
        fraction of price, to be treated as "the same level" (e.g. 0.0005
        means within 0.05% of each other).
    """

    lookback: int = 2
    equal_level_tolerance_pct: float = 0.0005

    def detect(self, candles: Sequence[Candle]) -> list[LiquidityZone]:
        swing_zones = self._find_swing_points(candles)
        return self._merge_equal_levels(swing_zones)

    def _find_swing_points(self, candles: Sequence[Candle]) -> list[LiquidityZone]:
        zones: list[LiquidityZone] = []
        lb = self.lookback
        n = len(candles)

        for i in range(lb, n - lb):
            candle = candles[i]
            window = candles[i - lb : i + lb + 1]

            if candle.high == max(c.high for c in window):
                zones.append(
                    LiquidityZone(
                        symbol=candle.symbol,
                        timeframe=candle.timeframe,
                        side=LiquiditySide.BUYSIDE,
                        liquidity_type=LiquidityType.SWING_HIGH,
                        price=candle.high,
                        created_at=candle.timestamp,
                    )
                )

            if candle.low == min(c.low for c in window):
                zones.append(
                    LiquidityZone(
                        symbol=candle.symbol,
                        timeframe=candle.timeframe,
                        side=LiquiditySide.SELLSIDE,
                        liquidity_type=LiquidityType.SWING_LOW,
                        price=candle.low,
                        created_at=candle.timestamp,
                    )
                )

        return zones

    def _merge_equal_levels(
        self, zones: list[LiquidityZone]
    ) -> list[LiquidityZone]:
        merged: list[LiquidityZone] = []

        groupings = [
            (LiquiditySide.BUYSIDE, LiquidityType.SWING_HIGH, LiquidityType.EQUAL_HIGH),
            (LiquiditySide.SELLSIDE, LiquidityType.SWING_LOW, LiquidityType.EQUAL_LOW),
        ]

        for side, base_type, equal_type in groupings:
            group = sorted(
                (z for z in zones if z.side == side and z.liquidity_type == base_type),
                key=lambda z: z.price,
            )

            i = 0
            while i < len(group):
                cluster = [group[i]]
                j = i + 1
                while j < len(group) and self._is_equal_price(
                    cluster[0].price, group[j].price
                ):
                    cluster.append(group[j])
                    j += 1

                if len(cluster) > 1:
                    merged.append(self._build_equal_zone(cluster, equal_type))
                else:
                    merged.append(cluster[0])

                i = j

        return merged

    def _is_equal_price(self, price_a: float, price_b: float) -> bool:
        tolerance = price_a * self.equal_level_tolerance_pct
        return abs(price_a - price_b) <= tolerance

    def _build_equal_zone(
        self, cluster: list[LiquidityZone], equal_type: LiquidityType
    ) -> LiquidityZone:
        reference = cluster[0]
        avg_price = sum(z.price for z in cluster) / len(cluster)
        earliest = min(z.created_at for z in cluster)

        return replace(
            reference,
            liquidity_type=equal_type,
            price=avg_price,
            created_at=earliest,
            touches=len(cluster),
        )