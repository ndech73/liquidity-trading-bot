"""
idea8_signals.py
----------------
Generates signals for Idea #8:
  "On H1 candles, go long at the next candle's open if the last close is higher
   than the close 24 candles earlier. Go short if it is lower. Hold for exactly
   8 candles, then exit."

Rules:
  - Lookback: 24 candles
  - Signal at candle i uses only closes[i] and closes[i - 24] (zero look-ahead)
  - Exclusion filter: No entries when the signal candle closes at 20:00, 21:00 or 22:00 UTC
    (spread spikes during New York rollover / Asian switchover)
"""

import numpy as np
import pandas as pd


def generate_idea8_signals(h1_candles: pd.DataFrame, lookback: int = 24) -> pd.Series:
    """
    Computes H1 momentum signals (+1 Long, -1 Short, 0 Flat).
    """
    n = len(h1_candles)
    signals = np.zeros(n, dtype=int)

    if n <= lookback:
        return pd.Series(signals, index=h1_candles.index)

    closes = h1_candles["close"].to_numpy(dtype=float)
    times = h1_candles["time"]

    # Signal candle closes 1 hour after its open time
    # Convert close time from broker server time (Europe/Helsinki) to UTC
    close_times_utc = (times + pd.Timedelta(hours=1)).dt.tz_localize("Europe/Helsinki").dt.tz_convert("UTC")
    close_utc_hours = close_times_utc.dt.hour.to_numpy()

    # Spreads spike when signal candle closes at 20:00, 21:00, or 22:00 UTC
    is_spread_spike_close = np.isin(close_utc_hours, [20, 21, 22])

    for i in range(lookback, n):
        # Time exclusion filter
        if is_spread_spike_close[i]:
            continue

        diff = closes[i] - closes[i - lookback]
        if diff > 0:
            signals[i] = 1
        elif diff < 0:
            signals[i] = -1
        else:
            signals[i] = 0

    return pd.Series(signals, index=h1_candles.index)
