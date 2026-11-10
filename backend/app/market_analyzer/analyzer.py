"""
analyzer.py
-----------
Combines all market analysis tools into one unified cockpit dashboard:
  - atr             : Smoothed wave height.
  - bb_width        : Bollinger corridor width.
  - width_zscore    : Is the corridor unusually wild or quiet?
  - active_levels   : Active uncrossed peaks and valleys known up to now.
  - vpoc            : The single price where the most trading took place.
  - value_area_low  : Floor of the 70% value zone.
  - value_area_high : Ceiling of the 70% value zone.

GOLDEN RULE: Standing at candle `at`, we only ever use candles 0..at.
Zero peeking into the future.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.market_analyzer.liquidity import active_levels, liquidity_levels
from app.market_analyzer.volatility import atr, bollinger_width
from app.market_analyzer.volume_profile import value_area, volume_profile, vpoc


def _clean(value) -> Optional[float]:
    """Turns an empty number (NaN) into None, and everything else into a float."""
    if value is None or pd.isna(value):
        return None
    return float(value)


# ---------------------------------------------------------------
# 1. The Tamper-Proof Flight Folder
# ---------------------------------------------------------------

@dataclass(frozen=True)
class MarketState:
    """
    Everything the model knows about the market at candle `position`.
    A value is None when there is not enough history yet to calculate it.
    """

    position: int
    atr: Optional[float]
    bb_width: Optional[float]
    width_zscore: Optional[float]
    active_levels: pd.DataFrame
    vpoc: Optional[float]
    value_area_low: Optional[float]
    value_area_high: Optional[float]


# ---------------------------------------------------------------
# 2. The Master Dashboard
# ---------------------------------------------------------------

class MarketAnalyzer:
    """
    Give it the candles once. Then call state_at(row_number) as many times
    as you like for instant O(1) lookups.
    """

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

        # Heavy math calculated ONCE in advance
        self._atr = atr(candles, atr_period)
        self._width = bollinger_width(candles["close"], bb_period, bb_std)
        self._zscore = self._make_zscore(self._width, zscore_window)
        self._levels = liquidity_levels(candles, swing_left, swing_right)

    @staticmethod
    def _make_zscore(width: pd.Series, window: int) -> pd.Series:
        """
        z-score = (today's width - past average width) / past standard deviation.
        .shift(1) guarantees today is never part of its own comparison.
        """
        history = width.rolling(window=window)
        past_mean = history.mean().shift(1)
        past_std = history.std(ddof=0).shift(1)

        return (width - past_mean) / past_std.where(past_std > 0)

    def state_at(self, at: int) -> MarketState:
        """The full market picture at candle number `at` (0 = first candle)."""
        if not 0 <= at < len(self.candles):
            raise ValueError(
                f"`at` must be between 0 and {len(self.candles) - 1}, got {at}"
            )

        # Volume profile: only the last `profile_window` candles, ending at `at`.
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
            # "swept_at" is dropped on purpose. A level that is still active
            # has not been crossed yet, so that column could only hold a
            # FUTURE candle number (or be empty). Handing it out would let
            # a trading rule peek at when the level gets swept later.
            active_levels=active_levels(self._levels, at).drop(columns=["swept_at"]),
            vpoc=vpoc(profile),
            value_area_low=area_low,
            value_area_high=area_high,
        )