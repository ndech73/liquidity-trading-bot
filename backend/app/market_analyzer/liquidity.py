"""
liquidity.py
------------
Finds the places where liquidity (waiting orders) is likely to sit.

Two tools live in this file so far:
  1. swing_points     - small peaks (swing highs) and small valleys (swing lows).
  2. liquidity_levels - turns those swings into price levels, and tracks
                        which levels are still active (not yet swept).

We will add the volume profile and VPOC in the next steps.
"""

import pandas as pd


# ---------------------------------------------------------------
# Tool 1: swing highs and swing lows
# ---------------------------------------------------------------

def swing_points(
    candles: pd.DataFrame, left: int = 2, right: int = 2
) -> pd.DataFrame:
    """
    Marks swing highs (small peaks) and swing lows (small valleys).

    `candles` is a table with these columns: high, low.
    Each row is one candle.

    A candle is a swing high if its high is HIGHER than the `left` candles
    before it and the `right` candles after it.
    A candle is a swing low if its low is LOWER than those same neighbours.

    Returns a table with two True/False columns:
      is_swing_high, is_swing_low

    WARNING (look-ahead): a swing at candle i is only KNOWN `right` candles
    later, because it needs the candles after it to be confirmed.
    """
    high = candles["high"]
    low = candles["low"]

    # Start by assuming every candle is a swing, then rule candles out.
    is_swing_high = pd.Series(True, index=candles.index)
    is_swing_low = pd.Series(True, index=candles.index)

    # Compare with the candles BEFORE.
    # shift(k) gives us the candle that is k steps earlier.
    for k in range(1, left + 1):
        is_swing_high &= high > high.shift(k)
        is_swing_low &= low < low.shift(k)

    # Compare with the candles AFTER.
    # shift(-k) gives us the candle that is k steps later.
    for k in range(1, right + 1):
        is_swing_high &= high > high.shift(-k)
        is_swing_low &= low < low.shift(-k)

    return pd.DataFrame(
        {
            "is_swing_high": is_swing_high,
            "is_swing_low": is_swing_low,
        }
    )


# ---------------------------------------------------------------
# Tool 2: liquidity levels
# ---------------------------------------------------------------

LEVEL_COLUMNS = ["position", "kind", "price", "known_at", "swept_at"]


def _first_position_beyond(prices, start, level, above):
    """
    Looks at the candles AFTER `start` and returns the row number of the
    first one that trades strictly beyond `level`.

    above=True  -> looks for a price higher than the level (a swing high).
    above=False -> looks for a price lower than the level (a swing low).
    Returns None if price never goes beyond the level.
    """
    later = prices[start + 1:]
    broken = later > level if above else later < level

    if not broken.any():
        return None

    # argmax gives the position of the first True in `broken`.
    return start + 1 + int(broken.argmax())


def liquidity_levels(
    candles: pd.DataFrame, left: int = 2, right: int = 2
) -> pd.DataFrame:
    """
    Turns every swing point into a liquidity level.

    `candles` is a table with these columns: high, low.

    Returns one row per level, with these columns:
      position  - the candle (row number) that made the swing
      kind      - "swing_high" (orders above the market)
                  or "swing_low" (orders below the market)
      price     - the level itself
      known_at  - the candle where we can first KNOW the swing is real
      swept_at  - the first candle that traded beyond the level
                  (empty if the level has never been swept)
    """
    swings = swing_points(candles, left, right)
    is_high = swings["is_swing_high"].to_numpy()
    is_low = swings["is_swing_low"].to_numpy()
    highs = candles["high"].to_numpy()
    lows = candles["low"].to_numpy()

    rows = []
    for position in range(len(candles)):
        if is_high[position]:
            rows.append(
                {
                    "position": position,
                    "kind": "swing_high",
                    "price": float(highs[position]),
                    "known_at": position + right,
                    "swept_at": _first_position_beyond(
                        highs, position, highs[position], above=True
                    ),
                }
            )
        if is_low[position]:
            rows.append(
                {
                    "position": position,
                    "kind": "swing_low",
                    "price": float(lows[position]),
                    "known_at": position + right,
                    "swept_at": _first_position_beyond(
                        lows, position, lows[position], above=False
                    ),
                }
            )

    levels = pd.DataFrame(rows, columns=LEVEL_COLUMNS)

    # "Int64" (capital I) is a whole-number column that is allowed to be empty.
    levels["swept_at"] = levels["swept_at"].astype("Int64")
    return levels


def active_levels(levels: pd.DataFrame, at: int) -> pd.DataFrame:
    """
    The levels the model is allowed to use when standing at candle `at`.

    A level is active if BOTH are true:
      1. It is already known:   known_at <= at   (no peeking into the future)
      2. It is not yet swept:   never swept, or swept AFTER candle `at`
    """
    is_known = levels["known_at"] <= at

    swept_later = (levels["swept_at"] > at).fillna(False).astype(bool)
    not_swept_yet = levels["swept_at"].isna() | swept_later

    return levels[is_known & not_swept_yet]