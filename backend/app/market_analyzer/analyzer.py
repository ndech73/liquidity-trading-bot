"""
analyzer.py
-----------
Combines all the Stage 1 tools into ONE answer about the market.

You point the analyzer at one candle (row number `at`) and it tells you:
  - atr             : how far a normal candle moves right now
  - bb_width        : how spread out recent closes are
  - width_zscore    : is that spread unusual compared with its OWN recent
                      history? (big positive = wild, big negative = very quiet)
  - active_levels   : liquidity levels that are known and not yet swept
  - vpoc            : price where the most trading happened recently
  - value_area_low / value_area_high : the zone holding ~70% of the volume

GOLDEN RULE: standing at candle `at`, we only use candles 0..at.
Never anything after it. (No peeking into the future.)
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
# The answer: a small package holding everything we know at one candle
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
# The analyzer
# ---------------------------------------------------------------

class MarketAnalyzer:
    """
    Give it the candles once. Then call state_at(row_number) as many times
    as you like.

    `candles` is a table with these columns: high, low, close, volume.
    `bin_size` is the width of one price bucket for the volume profile
    (for example 0.0001 = 1 pip on EURUSD).

    Settings (all have sensible defaults):
      atr_period      - how many candles ATR averages over
      bb_period       - how many closes the Bollinger bands use
      bb_std          - how many standard deviations wide the bands are
      zscore_window   - how many past width values we compare against
      profile_window  - how many recent candles feed the volume profile
      swing_left / swing_right - candles needed on each side of a swing
      value_share     - share of volume the value area must hold (0.70 = 70%)
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

        # --- Heavy maths, done ONCE ---------------------------------
        # Each of these only looks at the past, so it is safe to calculate
        # them for all candles at the start.
        self._atr = atr(candles, atr_period)

        self._width = bollinger_width(candles["close"], bb_period, bb_std)
        self._zscore = self._make_zscore(self._width, zscore_window)

        # Liquidity levels carry their own "known_at" and "swept_at" labels,
        # and active_levels() uses them to hide anything from the future.
        self._levels = liquidity_levels(candles, swing_left, swing_right)

    @staticmethod
    def _make_zscore(width: pd.Series, window: int) -> pd.Series:
        """
        z-score = (today's width - average past width) / spread of past widths.

        "Past" means the `window` candles BEFORE this one. We use shift(1)
        so today's own value is never part of its own comparison.

        Reading it:   0 = normal,   +2 = unusually wild,   -2 = unusually quiet.
        """
        history = width.rolling(window=window)
        past_mean = history.mean().shift(1)
        past_std = history.std(ddof=0).shift(1)

        # If the past never moved at all (std = 0) we cannot divide by it,
        # so we leave that answer empty.
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
            active_levels=active_levels(self._levels, at),
            vpoc=vpoc(profile),
            value_area_low=area_low,
            value_area_high=area_high,
        )