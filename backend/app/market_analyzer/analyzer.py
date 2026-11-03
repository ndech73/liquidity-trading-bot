from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.market_analyzer.liquidity import active_levels, liquidity_levels
from app.market_analyzer.volatility import atr, bollinger_width
from app.market_analyzer.volume_profile import value_area, volume_profile, vpoc


def _clean(value) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    return float(value)


# ---------------------------------------------------------------
# 1. The Package: Everything known at one single moment in time
# ---------------------------------------------------------------

@dataclass(frozen=True)
class MarketState:
    position: int
    atr: Optional[float]
    bb_width: Optional[float]
    width_zscore: Optional[float]
    active_levels: pd.DataFrame
    vpoc: Optional[float]
    value_area_low: Optional[float]
    value_area_high: Optional[float]


# ---------------------------------------------------------------
# 2. The Master Dashboard (MarketAnalyzer)
# ---------------------------------------------------------------

class MarketAnalyzer:
    def __init__(
        self,
        candles: pd.DataFrame,
        bin_size: float,
        atr_period: int = 14,
        bb_period: int = 20,
        bb_std: float = 2.0,
        zscore_window: int = 100,
        profile_window: int = 200,
        swing_left: int = 2,
        swing_right: int = 2,
        value_share: float = 0.70,
    ):
        self.candles = candles
        self.bin_size = bin_size
        self.profile_window = profile_window
        self.value_share = value_share

        # Heavy math calculated once across the entire series
        self._atr = atr(candles, atr_period)
        self._width = bollinger_width(candles["close"], bb_period, bb_std)
        self._zscore = self._make_zscore(self._width, zscore_window)
        self._levels = liquidity_levels(candles, swing_left, swing_right)

    @staticmethod
    def _make_zscore(width: pd.Series, window: int) -> pd.Series:
        history = width.rolling(window=window)
        past_mean = history.mean().shift(1)
        past_std = history.std(ddof=0).shift(1)

        return (width - past_mean) / past_std.where(past_std > 0)

    def state_at(self, at: int) -> MarketState:
        if not 0 <= at < len(self.candles):
            raise ValueError(
                f"`at` must be between 0 and {len(self.candles) - 1}, got {at}"
            )

        start = max(0, at - self.profile_window + 1)
        recent = self.candles.iloc[start : at + 1]
        profile = volume_profile(recent, self.bin_size)

        area = value_area(profile, self.value_share)
        area_low, area_high = area if area is not None else (None, None)

        return MarketState(
            position=at,
            atr=_clean(self._atr.iloc[at]),
            bb_width=_clean(self._width.iloc[at]),
            width_zscore=_clean(self._zscore.iloc[at]),
            active_levels=active_levels(self._levels, at),
            vpoc=vpoc(profile),
            value_area_low=area_low,
            value_area_high=area_high,
        )