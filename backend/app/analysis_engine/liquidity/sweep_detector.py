from ..domain.candle import Candle
from ..domain.liquidity import LiquidityStatus, LiquidityType, LiquidityZone


LOW_TYPES = {
    LiquidityType.SWING_LOW,
    LiquidityType.EQUAL_LOW,
    LiquidityType.SESSION_LOW,
    LiquidityType.PREVIOUS_LOW,
}

HIGH_TYPES = {
    LiquidityType.SWING_HIGH,
    LiquidityType.EQUAL_HIGH,
    LiquidityType.SESSION_HIGH,
    LiquidityType.PREVIOUS_HIGH,
}


class SweepDetector:
    def check(self, candle: Candle, zone: LiquidityZone) -> bool:
        if zone.status != LiquidityStatus.ACTIVE:
            return False

        if zone.liquidity_type in LOW_TYPES:
            return candle.low < zone.price

        if zone.liquidity_type in HIGH_TYPES:
            return candle.high > zone.price

        return False
