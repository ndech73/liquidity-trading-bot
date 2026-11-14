"""
downloader.py
-------------
Gets candles from MetaTrader 5 and saves them as CSV files.

Two parts:
  1. rates_to_candles - cleans the raw MT5 numbers into a tidy table.
                        (No MT5 needed, so it can be tested.)
  2. download_candles - the only code that talks to MT5.

Files are saved in  backend/data_files/  as  SYMBOL_TIMEFRAME.csv
(for example EURUSD_M15.csv). That folder is gitignored.

IMPORTANT: the times are BROKER SERVER TIME, exactly as MT5 gives them.
They are not UTC. We will deal with this before we build session rules
(like the 07:00-18:00 killzone).
"""

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# backend/data_files  (this file is backend/app/data/downloader.py)
DATA_DIR = Path(__file__).resolve().parents[2] / "data_files"

CANDLE_COLUMNS = ["time", "open", "high", "low", "close", "volume", "spread"]

# MT5 asks for data in chunks, so one huge request never gets cut short.
CHUNK_DAYS = 90

# How many times to ask again if MT5 answers with nothing
# (MT5 sometimes needs a moment to load history the first time).
RETRIES = 3


# ---------------------------------------------------------------
# Part 1: clean the raw MT5 numbers (no MT5 needed)
# ---------------------------------------------------------------

def rates_to_candles(rates: pd.DataFrame) -> pd.DataFrame:
    """
    Turns the raw table from MT5 into our standard candle table.

    MT5 gives columns: time, open, high, low, close, tick_volume,
    spread, real_volume. Time is a count of seconds.

    We return: time, open, high, low, close, volume, spread
      - time   is a real date and time
      - volume is MT5's tick volume (forex has no real traded volume)
    Rows are sorted by time, and repeated times are removed.
    """
    candles = pd.DataFrame(
        {
            "time": pd.to_datetime(rates["time"], unit="s"),
            "open": rates["open"].astype(float),
            "high": rates["high"].astype(float),
            "low": rates["low"].astype(float),
            "close": rates["close"].astype(float),
            "volume": rates["tick_volume"].astype(float),
            "spread": rates["spread"].astype(float),
        }
    )

    candles = candles.sort_values("time")
    candles = candles.drop_duplicates(subset="time", keep="first")
    return candles.reset_index(drop=True)[CANDLE_COLUMNS]


def candle_file(symbol: str, timeframe: str, folder: Path = DATA_DIR) -> Path:
    """Where the file for this symbol and timeframe lives."""
    return Path(folder) / f"{symbol}_{timeframe}.csv"


def save_candles(
    candles: pd.DataFrame, symbol: str, timeframe: str, folder: Path = DATA_DIR
) -> Path:
    """Saves the candles to a CSV file and returns the file's path."""
    path = candle_file(symbol, timeframe, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    candles.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------
# Part 2: talk to MT5 (needs the Wine bridge running)
# ---------------------------------------------------------------

def download_candles(
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    chunk_days: int = CHUNK_DAYS,
    host: str = "127.0.0.1",
    port: int = 18812,
) -> pd.DataFrame:
    """
    Downloads candles from MT5 between `start` and `end`.

    `timeframe` is a name like "M15", "H1" or "H4".
    The bridge must already be running (scripts/start_mt5_bridge.sh).

    How it works: we connect to the small listener running inside Wine,
    and borrow the real MetaTrader5 package that lives on that side.
    """
    import rpyc  # imported here so tests never need it

    conn = rpyc.classic.connect(host, port)
    mt5 = conn.modules.MetaTrader5

    try:
        if not mt5.initialize():
            raise RuntimeError(f"Could not connect to MT5: {mt5.last_error()}")

        if not mt5.symbol_select(symbol, True):  # make sure the symbol is switched on
            raise RuntimeError(f"MT5 does not know the symbol {symbol}")

        tf_constant = getattr(mt5, f"TIMEFRAME_{timeframe}", None)
        if tf_constant is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")

        start = start.replace(tzinfo=timezone.utc)
        end = end.replace(tzinfo=timezone.utc)

        pieces = []
        chunk_start = start
        while chunk_start < end:
            chunk_end = min(chunk_start + timedelta(days=chunk_days), end)

            # MT5 wants real dates on ITS side, so we copy ours across.
            remote_start = rpyc.classic.deliver(conn, chunk_start)
            remote_end = rpyc.classic.deliver(conn, chunk_end)

            rates = None
            for _ in range(RETRIES):
                rates = mt5.copy_rates_range(
                    symbol, tf_constant, remote_start, remote_end
                )
                if rates is not None and len(rates) > 0:
                    break
                time.sleep(2)

            if rates is not None and len(rates) > 0:
                # Copy the numbers from the Wine side to our side.
                pieces.append(pd.DataFrame(rpyc.classic.obtain(rates)))

            chunk_start = chunk_end

        if not pieces:
            raise RuntimeError(f"MT5 returned no candles for {symbol} {timeframe}")

        return rates_to_candles(pd.concat(pieces, ignore_index=True))
    finally:
        try:
            mt5.shutdown()
        finally:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Download candles from MT5.")
    parser.add_argument("symbols", nargs="+", help="for example EURUSD GBPUSD")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--chunk-days", type=int, default=CHUNK_DAYS, help=f"Days per request chunk (default: {CHUNK_DAYS})")
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")

    for symbol in args.symbols:
        candles = download_candles(symbol, args.timeframe, start, end, chunk_days=args.chunk_days)
        path = save_candles(candles, symbol, args.timeframe)
        print(f"{symbol}: {len(candles)} candles saved to {path}")


if __name__ == "__main__":
    main()