"""
volatility.py
-------------
Measures how much price is moving.

Two tools live in this file:
  1. ATR (Average True Range)    - how far a normal candle moves.
  2. Bollinger Band width        - how spread out recent closing prices are.
"""

import pandas as pd


# ---------------------------------------------------------------
# Tool 1: ATR
# ---------------------------------------------------------------

def true_range(candles: pd.DataFrame) -> pd.Series:
    """
    Size of each candle, including any jump from the previous candle.

    `candles` is a table with these columns: high, low, close.
    Each row is one candle (for example, one 15-minute candle).
    """
    # The close of the candle before this one.
    previous_close = candles["close"].shift(1)

    # Three ways to measure the candle's movement:
    candle_size = candles["high"] - candles["low"]
    up_from_previous_close = (candles["high"] - previous_close).abs()
    down_from_previous_close = (candles["low"] - previous_close).abs()

    # Keep the biggest of the three for each candle.
    # (The very first candle has no previous close, so only candle_size is used.)
    all_three = pd.concat(
        [candle_size, up_from_previous_close, down_from_previous_close],
        axis=1,
    )
    return all_three.max(axis=1)


def atr(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range: the typical candle movement over the last `period` candles.

    The first (period - 1) rows are empty (NaN), because there are
    not enough candles yet to calculate a fair average.
    """
    tr = true_range(candles)

    # Wilder's smoothing: each new ATR = a little of the new candle
    # + a lot of the old ATR. The "1 / period" is how much weight the new candle gets.
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


# ---------------------------------------------------------------
# Tool 2: Bollinger Bands and their width
# ---------------------------------------------------------------

def bollinger_bands(
    close: pd.Series, period: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    """
    Three lines drawn around the closing prices:
      middle = the average of the last `period` closes
      upper  = middle + num_std standard deviations
      lower  = middle - num_std standard deviations

    The first (period - 1) rows are empty (NaN), because there are
    not enough closes yet.
    """
    # The rolling window looks at the last `period` closes, one candle at a time.
    window = close.rolling(window=period)

    middle = window.mean()

    # ddof=0 means "divide by N" (population standard deviation),
    # which is what Bollinger's original method uses.
    # (pandas uses ddof=1 by default, which divides by N - 1.)
    std = window.std(ddof=0)

    return pd.DataFrame(
        {
            "middle": middle,
            "upper": middle + num_std * std,
            "lower": middle - num_std * std,
        }
    )


def bollinger_width(
    close: pd.Series, period: int = 20, num_std: float = 2.0
) -> pd.Series:
    """
    Bollinger Band width: the gap between the upper and lower band,
    as a share of the middle line.

    Small number = squeeze (quiet market, prices bunched together).
    Big number   = expansion (wild market, prices spread out).
    """
    bands = bollinger_bands(close, period, num_std)
    return (bands["upper"] - bands["lower"]) / bands["middle"]