"""
liquidity.py
------------
Finds local market peaks and valleys and tracks tripwires without looking into the future:
  1. swing_points          - Identifies local maximums (peaks) and minimums (valleys).
  2. _first_position_beyond - Pinpoints the exact candle where a level is first swept.
  3. liquidity_levels      - Master logbook with strict anti-cheating `known_at` timestamps.
  4. active_levels         - Filters only what is legally known and uncrossed at candle `at`.
"""

import pandas as pd


# ---------------------------------------------------------------
# 1. Finding Local Peaks and Valleys
# ---------------------------------------------------------------

def swing_points(
    candles: pd.DataFrame, left: int = 2, right: int = 2
) -> pd.DataFrame:
    high = candles["high"]
    low = candles["low"]

    is_swing_high = pd.Series(True, index=candles.index)
    is_swing_low = pd.Series(True, index=candles.index)

    for k in range(1, left + 1):
        is_swing_high &= high > high.shift(k)
        is_swing_low &= low < low.shift(k)

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
# 2. Tracking When Levels Get Crossed (Swept)
# ---------------------------------------------------------------

LEVEL_COLUMNS = ["position", "kind", "price", "known_at", "swept_at"]


def _first_position_beyond(prices, start, level, above):
    later = prices[start + 1:]
    broken = later > level if above else later < level

    if not broken.any():
        return None

    return start + 1 + int(broken.argmax())


def liquidity_levels(
    candles: pd.DataFrame, left: int = 2, right: int = 2
) -> pd.DataFrame:
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
    levels["swept_at"] = levels["swept_at"].astype("Int64")
    return levels


# ---------------------------------------------------------------
# 3. Active Levels (Only what is currently known and uncrossed)
# ---------------------------------------------------------------

def active_levels(levels: pd.DataFrame, at: int) -> pd.DataFrame:
    is_known = levels["known_at"] <= at
    swept_later = (levels["swept_at"] > at).fillna(False).astype(bool)
    not_swept_yet = levels["swept_at"].isna() | swept_later

    return levels[is_known & not_swept_yet]