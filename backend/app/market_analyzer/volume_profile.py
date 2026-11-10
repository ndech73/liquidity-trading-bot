"""
volume_profile.py
-----------------
Shows at which prices most trading activity actually took place:
  1. volume_profile - Groups prices into discrete buckets (bins) and tallies volume.
  2. vpoc           - Volume Point of Control: the single fullest bucket (Mode).
  3. value_area     - The 70% core price boundaries (VAL and VAH).
"""

import numpy as np
import pandas as pd


PROFILE_COLUMNS = ["price_low", "price_high", "volume"]
_TINY = 1e-9


# ---------------------------------------------------------------
# 1. Volume Profile (The Price Histogram)
# ---------------------------------------------------------------

def volume_profile(candles: pd.DataFrame, bin_size: float) -> pd.DataFrame:
    if bin_size <= 0:
        raise ValueError("bin_size must be bigger than zero")

    if candles.empty:
        return pd.DataFrame(columns=PROFILE_COLUMNS)

    low_bins = np.floor(candles["low"].to_numpy() / bin_size + _TINY).astype(int)
    high_bins = np.floor(candles["high"].to_numpy() / bin_size + _TINY).astype(int)
    volumes = candles["volume"].to_numpy(dtype=float)

    first_bin = low_bins.min()
    last_bin = high_bins.max()
    totals = np.zeros(last_bin - first_bin + 1)

    for low_bin, high_bin, volume in zip(low_bins, high_bins, volumes):
        buckets_touched = high_bin - low_bin + 1
        share = volume / buckets_touched
        totals[low_bin - first_bin : high_bin - first_bin + 1] += share

    bin_numbers = np.arange(first_bin, last_bin + 1)
    return pd.DataFrame(
        {
            "price_low": bin_numbers * bin_size,
            "price_high": (bin_numbers + 1) * bin_size,
            "volume": totals,
        }
    )


# ---------------------------------------------------------------
# 2. VPOC (The Single Most Popular Price)
# ---------------------------------------------------------------

def vpoc(profile: pd.DataFrame):
    if profile.empty:
        return None

    fullest = profile["volume"].idxmax()
    bottom = profile.loc[fullest, "price_low"]
    top = profile.loc[fullest, "price_high"]
    return float((bottom + top) / 2)


# ---------------------------------------------------------------
# 3. Value Area (The 70% Core Zone)
# ---------------------------------------------------------------

def value_area(profile: pd.DataFrame, share: float = 0.70):
    if not 0 < share <= 1:
        raise ValueError("share must be bigger than 0 and at most 1")

    if profile.empty:
        return None

    volumes = profile["volume"].to_numpy(dtype=float)
    total = volumes.sum()
    if total <= 0:
        return None

    target = share * total
    low = high = int(np.argmax(volumes))
    collected = volumes[low]

    while collected < target - _TINY:
        can_go_down = low > 0
        can_go_up = high < len(volumes) - 1

        if not can_go_down and not can_go_up:
            break

        volume_below = volumes[low - 1] if can_go_down else -1.0
        volume_above = volumes[high + 1] if can_go_up else -1.0

        if volume_below >= volume_above:
            low -= 1
            collected += volumes[low]
        else:
            high += 1
            collected += volumes[high]

    value_area_low = float(profile["price_low"].iloc[low])
    value_area_high = float(profile["price_high"].iloc[high])
    return value_area_low, value_area_high