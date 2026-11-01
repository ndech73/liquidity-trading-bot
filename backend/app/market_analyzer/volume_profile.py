"""
volume_profile.py
-----------------
Shows WHERE (at which prices) most of the trading happened.

Three tools live in this file:
  1. volume_profile - splits the price range into small buckets (bins) and
                      counts how much volume fell into each bucket.
  2. vpoc           - the Volume Point of Control: the middle of the
                      fullest bucket.
  3. value_area     - the price range around the VPOC that holds most
                      (usually 70%) of all the volume.

Note: forex has no central exchange, so "volume" here means TICK volume
(how many times price changed), not real traded amounts.
"""

import numpy as np
import pandas as pd


PROFILE_COLUMNS = ["price_low", "price_high", "volume"]

# A tiny number added before rounding down. Computers store decimals like
# 1.1000 / 0.0001 as 10999.999999999998, which would land in the wrong
# bucket. Adding a tiny number fixes that.
_TINY = 1e-9


# ---------------------------------------------------------------
# Tool 1: volume profile
# ---------------------------------------------------------------

def volume_profile(candles: pd.DataFrame, bin_size: float) -> pd.DataFrame:
    """
    Counts how much volume sits in each price bucket.

    `candles` is a table with these columns: high, low, volume.
    `bin_size` is the width of each bucket, in price units
    (for example 0.0001 = 1 pip on EURUSD).

    Each candle's volume is spread EVENLY across the buckets between
    its low and its high.

    Returns one row per bucket, from the lowest price to the highest:
      price_low   - bottom edge of the bucket
      price_high  - top edge of the bucket
      volume      - total volume that fell into the bucket
    """
    if bin_size <= 0:
        raise ValueError("bin_size must be bigger than zero")

    if candles.empty:
        return pd.DataFrame(columns=PROFILE_COLUMNS)

    # Which bucket number does each low and each high fall into?
    # Bucket number = price divided by bucket width, rounded DOWN.
    low_bins = np.floor(candles["low"].to_numpy() / bin_size + _TINY).astype(int)
    high_bins = np.floor(candles["high"].to_numpy() / bin_size + _TINY).astype(int)
    volumes = candles["volume"].to_numpy(dtype=float)

    # The profile runs from the lowest bucket ever touched to the highest.
    first_bin = low_bins.min()
    last_bin = high_bins.max()
    totals = np.zeros(last_bin - first_bin + 1)

    for low_bin, high_bin, volume in zip(low_bins, high_bins, volumes):
        buckets_touched = high_bin - low_bin + 1
        share = volume / buckets_touched

        # Add an equal share to every bucket this candle touched.
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
# Tool 2: VPOC
# ---------------------------------------------------------------

def vpoc(profile: pd.DataFrame):
    """
    Volume Point of Control: the middle price of the fullest bucket.

    `profile` is the table returned by volume_profile().
    If two buckets are tied, the LOWER price wins.
    Returns None if the profile is empty.
    """
    if profile.empty:
        return None

    # idxmax gives the first fullest bucket. The profile runs from low to
    # high price, so "first" means "lowest price" when there is a tie.
    fullest = profile["volume"].idxmax()

    bottom = profile.loc[fullest, "price_low"]
    top = profile.loc[fullest, "price_high"]
    return float((bottom + top) / 2)


# ---------------------------------------------------------------
# Tool 3: value area
# ---------------------------------------------------------------

def value_area(profile: pd.DataFrame, share: float = 0.70):
    """
    The price range around the VPOC that holds at least `share` of all
    the volume (0.70 = 70%).

    `profile` is the table returned by volume_profile().

    We start with the fullest bucket (the VPOC) and grow the zone one
    bucket at a time. Each time, we compare the next bucket ABOVE with the
    next bucket BELOW and add the one with more volume. In a tie, the
    LOWER bucket wins. If one side has run out, we use the other side.

    Returns (value_area_low, value_area_high), or None if there is no volume.
    """
    if not 0 < share <= 1:
        raise ValueError("share must be bigger than 0 and at most 1")

    if profile.empty:
        return None

    volumes = profile["volume"].to_numpy(dtype=float)
    total = volumes.sum()
    if total <= 0:
        return None

    target = share * total

    # argmax gives the first fullest bucket (the lowest price in a tie),
    # the same rule as vpoc().
    low = high = int(np.argmax(volumes))
    collected = volumes[low]

    # Keep growing until the zone holds enough volume.
    # (The tiny number protects us from decimal rounding errors.)
    while collected < target - _TINY:
        can_go_down = low > 0
        can_go_up = high < len(volumes) - 1

        if not can_go_down and not can_go_up:
            break  # the zone already covers the whole profile

        # -1 means "no bucket on that side", so the other side always wins.
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