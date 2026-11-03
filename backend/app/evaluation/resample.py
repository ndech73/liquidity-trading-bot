"""
resample.py
-----------
Builds complete H1 (4 x M15) and H4 (16 x M15) candles from M15 candle data.

Aggregation rules:
  - open         : first M15 open
  - high         : highest M15 high
  - low          : lowest M15 low
  - close        : last M15 close
  - volume       : sum of M15 volume
  - spread_worst : highest M15 spread (conservative cost)
  - spread_avg   : mean M15 spread
  - spread       : alias for spread_worst

Incomplete candle rule:
  - Any H1 period with fewer than 4 M15 candles is dropped.
  - Any H4 period with fewer than 16 M15 candles is dropped.
"""

import pandas as pd


def resample_m15(candles: pd.DataFrame, target: str) -> tuple[pd.DataFrame, int]:
    """
    Resamples M15 candles to H1 or H4.

    target: "H1" or "H4"
    Returns (resampled_df, dropped_incomplete_count)
    """
    target = target.upper()
    if target not in ("H1", "H4"):
        raise ValueError(f"target must be 'H1' or 'H4', got {target}")

    req_pieces = 4 if target == "H1" else 16
    freq = "1h" if target == "H1" else "4h"

    floored_time = candles["time"].dt.floor(freq)
    counts = candles.groupby(floored_time).size()

    complete_keys = counts[counts == req_pieces].index
    dropped_count = int((counts < req_pieces).sum())

    complete_mask = floored_time.isin(complete_keys)
    filtered_candles = candles[complete_mask]

    grouped = filtered_candles.groupby(filtered_candles["time"].dt.floor(freq))

    res = grouped.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        spread_worst=("spread", "max"),
        spread_avg=("spread", "mean"),
    ).reset_index()

    res = res.rename(columns={"index": "time"})
    res["spread"] = res["spread_worst"]

    return res, dropped_count
