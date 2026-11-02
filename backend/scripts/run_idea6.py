"""
run_idea6.py
------------
Runs the edge evaluation for Idea #6 (Asian Range Sweep at London Open)
following RULES.md across all 6 pairs on development data.

Idea #6 Rule:
  Asian session (00:00 to 07:45 server time) defines the daily reference range:
    asian_high = max high in Asian session
    asian_low  = min low in Asian session
  During London open (08:00 to 12:00 server time):
  - Long  : first candle sweeping below asian_low AND closing above asian_low
  - Short : first candle sweeping above asian_high AND closing below asian_high
  (Maximum 1 signal per day per pair)
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.loader import load_candles
from app.evaluation.edge_stats import evaluate_edge, format_report
from app.evaluation.outcomes import build_trades
from app.market_analyzer.volatility import atr

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY"]
TIMEFRAME = "M15"
HORIZON = 8
ASIAN_END_HOUR = 8      # Asian session: 00:00 to 07:45
LONDON_START_HOUR = 8   # London open: 08:00 to 12:00
LONDON_END_HOUR = 12
K = 6


def generate_signals_for_pair(candles: pd.DataFrame) -> pd.Series:
    n = len(candles)
    signals = np.zeros(n, dtype=int)

    dates = candles["time"].dt.date.to_numpy()
    hours = candles["time"].dt.hour.to_numpy()
    highs = candles["high"].to_numpy(dtype=float)
    lows = candles["low"].to_numpy(dtype=float)
    closes = candles["close"].to_numpy(dtype=float)

    unique_dates = np.unique(dates)
    for d in unique_dates:
        day_mask = (dates == d)
        day_indices = np.where(day_mask)[0]
        if len(day_indices) == 0:
            continue

        asian_indices = day_indices[hours[day_indices] < ASIAN_END_HOUR]
        if len(asian_indices) < 4:
            continue

        asian_high = highs[asian_indices].max()
        asian_low = lows[asian_indices].min()

        london_indices = day_indices[
            (hours[day_indices] >= LONDON_START_HOUR) & (hours[day_indices] <= LONDON_END_HOUR)
        ]

        day_traded = False
        for i in london_indices:
            if i >= n - HORIZON:
                break
            if day_traded:
                break

            # Bullish sweep rejection (fade the break below Asian low)
            if lows[i] < asian_low and closes[i] > asian_low:
                signals[i] = 1
                day_traded = True
            # Bearish sweep rejection (fade the break above Asian high)
            elif highs[i] > asian_high and closes[i] < asian_high:
                signals[i] = -1
                day_traded = True

    return pd.Series(signals, index=candles.index)


def main():
    print(f"============================================================")
    print(f"Running Idea #6 Evaluation: Asian Range Sweep at London Open (k={K})")
    print(f"Pairs: {', '.join(PAIRS)} | Asian: 00:00-07:45 | London: 08:00-12:00 | Horizon: {HORIZON}")
    print(f"============================================================\n")

    all_trades_list = []
    t_start = time.time()

    for symbol in PAIRS:
        t0 = time.time()
        print(f"Loading {symbol}...", end=" ", flush=True)
        candles = load_candles(symbol, TIMEFRAME, part="development")
        atr_vals = atr(candles, 14)
        print(f"{len(candles):,} candles. Signals...", end=" ", flush=True)

        signals = generate_signals_for_pair(candles)
        sig_count = (signals != 0).sum()
        trades = build_trades(symbol, candles, signals, atr_vals, horizon=HORIZON)
        all_trades_list.append(trades)
        elapsed = time.time() - t0
        mo = float(trades["outcome_atr"].mean())
        mc = float(trades["cost_atr"].mean())
        print(f"{sig_count:,} sigs -> {len(trades):,} trades | Mean: {mo:+.4f} ATR | Cost: {mc:.4f} ATR ({elapsed:.1f}s)")

    combined_trades = pd.concat(all_trades_list, ignore_index=True)
    total_time = time.time() - t_start
    print(f"\nAll pairs processed in {total_time:.1f}s.")
    print(f"Total non-overlapping trades collected: {len(combined_trades):,}")

    print("\nRunning Edge Statistical Tests (A through E)...")
    report = evaluate_edge(combined_trades, k=K, seed=0)

    print("\n" + "=" * 60)
    print("EDGE EVALUATION REPORT (RULES.md Section 4)")
    print("=" * 60)
    report_text = format_report(report)
    print(report_text)
    print("=" * 60)

    return report


if __name__ == "__main__":
    main()
