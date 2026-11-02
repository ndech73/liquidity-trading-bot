"""
loader.py
---------
Reads saved candles back from a file and CHECKS they are clean.

Bad data is dangerous: one flipped high/low or a duplicate row can make a
backtest look better or worse than reality, and you would never notice.
So we stop with a clear error instead.
"""

from pathlib import Path

import pandas as pd

from app.data.downloader import CANDLE_COLUMNS, DATA_DIR, candle_file


def validate_candles(candles: pd.DataFrame) -> None:
    """
    Raises ValueError if the candles are not clean. Checks that:
      1. all the expected columns exist
      2. no value is empty
      3. time always moves forward (no duplicates, no wrong order)
      4. high is the highest and low is the lowest of each candle
      5. volume is never negative
    """
    missing = [c for c in CANDLE_COLUMNS if c not in candles.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if candles[CANDLE_COLUMNS].isna().any().any():
        raise ValueError("Candles contain empty values")

    if not candles["time"].is_monotonic_increasing or candles["time"].duplicated().any():
        raise ValueError("Candle times must be in order, with no repeats")

    top = candles[["open", "close", "low"]].max(axis=1)
    bottom = candles[["open", "close", "high"]].min(axis=1)
    if (candles["high"] < top).any() or (candles["low"] > bottom).any():
        raise ValueError("Some candles have a high below, or a low above, their prices")

    if (candles["volume"] < 0).any():
        raise ValueError("Volume cannot be negative")


def load_candles(symbol: str, timeframe: str, folder: Path = DATA_DIR) -> pd.DataFrame:
    """Reads the saved file, checks it, and returns the candles."""
    path = candle_file(symbol, timeframe, folder)
    if not path.exists():
        raise FileNotFoundError(
            f"No data file at {path}. Run the downloader for {symbol} {timeframe} first."
        )

    candles = pd.read_csv(path, parse_dates=["time"])
    validate_candles(candles)
    return candles


def find_gaps(candles: pd.DataFrame, min_hours: float = 6.0) -> pd.DataFrame:
    """
    Lists the places where time jumps by more than `min_hours`.

    Weekends show up as gaps of about 48 hours. That is NORMAL for forex.
    A gap in the middle of a trading week means missing data.
    """
    step = candles["time"].diff()
    is_gap = step > pd.Timedelta(hours=min_hours)

    gaps = pd.DataFrame(
        {
            "gap_start": candles["time"].shift(1)[is_gap],
            "gap_end": candles["time"][is_gap],
            "hours": step[is_gap].dt.total_seconds() / 3600,
        }
    )
    return gaps.reset_index(drop=True)