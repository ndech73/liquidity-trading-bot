"""
outcomes.py
-----------
Turns SIGNALS into TRADE OUTCOMES, following RULES.md section 3.

A signal is a number for every candle:
   +1 = go long,   -1 = go short,   0 = do nothing.
The signal at candle i may only use candles 0..i (the signal rule's job).

What this file does with each signal:
  - Entry : the OPEN of the next candle (i + 1).
  - Hold  : exactly `horizon` candles (8 candles of M15 = 2 hours),
            so the exit is the CLOSE of candle i + horizon.
  - Size  : price change from entry to exit, in the signal's direction,
            divided by ATR at the signal candle. The unit is "ATR".
  - Cost  : the spread recorded at the entry candle, in ATR.

Trades that are skipped (never counted):
  - A signal that fires while an earlier trade on the same pair is still open.
  - A trade whose candles are not back-to-back in time (it would cross a
    weekend or a hole in the data, so price could jump).
  - A signal with no ATR yet, or too close to the end of the data.
"""

import numpy as np
import pandas as pd

TRADE_COLUMNS = [
    "symbol",
    "signal_pos",
    "entry_time",
    "direction",
    "move_atr",     # price change entry -> exit in ATR, NOT yet turned around by direction
    "outcome_atr",  # direction * move_atr  (before costs)
    "cost_atr",     # spread paid, in ATR
    "week",
    "quarter",
]


def point_size(symbol: str) -> float:
    """
    The size of one MT5 "point" for this pair.
    JPY pairs have 3 decimals (point = 0.001); the others have 5 (point = 0.00001).
    The spread column in the data is counted in points.
    """
    return 0.001 if "JPY" in symbol.upper() else 0.00001


def _empty_trades() -> pd.DataFrame:
    return pd.DataFrame(columns=TRADE_COLUMNS)


def build_trades(
    symbol: str,
    candles: pd.DataFrame,
    signals: pd.Series,
    atr_values: pd.Series,
    horizon: int = 8,
    candle_minutes: int = 15,
) -> pd.DataFrame:
    """
    Builds the list of trades for ONE pair.

    `candles`    table with columns: time, open, close, spread
    `signals`    one number per candle: +1, -1 or 0 (same length as candles)
    `atr_values` one ATR number per candle (same length as candles).
                 Use app.market_analyzer.volatility.atr(candles, 14).
    """
    n = len(candles)
    if len(signals) != n or len(atr_values) != n:
        raise ValueError("signals and atr_values must have one value per candle")
    if horizon < 1:
        raise ValueError("horizon must be at least 1")

    sig = signals.to_numpy()
    if not np.isin(sig, [-1, 0, 1]).all():
        raise ValueError("signals may only contain -1, 0 or 1")

    atr_arr = atr_values.to_numpy(dtype=float)
    times = candles["time"].to_numpy()
    opens = candles["open"].to_numpy(dtype=float)
    closes = candles["close"].to_numpy(dtype=float)
    spreads = candles["spread"].to_numpy(dtype=float)

    point = point_size(symbol)
    step = np.timedelta64(candle_minutes, "m")

    rows = []
    free_from = 0  # the first candle where a new trade may start

    for i in np.flatnonzero(sig != 0):
        entry = i + 1
        exit_ = i + horizon

        if exit_ >= n:
            break  # too close to the end, and so is every later signal
        if entry < free_from:
            continue  # an earlier trade is still open
        if not atr_arr[i] > 0:
            continue  # no ATR yet (empty) or a broken value
        if times[exit_] - times[i] != horizon * step:
            continue  # candles are not back-to-back: weekend or missing data

        direction = int(sig[i])
        move = (closes[exit_] - opens[entry]) / atr_arr[i]

        rows.append(
            {
                "symbol": symbol,
                "signal_pos": int(i),
                "entry_time": pd.Timestamp(times[entry]),
                "direction": direction,
                "move_atr": float(move),
                "outcome_atr": float(direction * move),
                "cost_atr": float(spreads[entry] * point / atr_arr[i]),
            }
        )
        free_from = entry + horizon  # this trade uses candles entry .. exit_

    if not rows:
        return _empty_trades()

    trades = pd.DataFrame(rows)
    trades["week"] = trades["entry_time"].dt.to_period("W").astype(str)
    trades["quarter"] = trades["entry_time"].dt.to_period("Q").astype(str)
    return trades[TRADE_COLUMNS]
