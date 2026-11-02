"""
run_idea4.py
------------
Runs the edge evaluation for Idea #4 (Major Structural Failed Auction Reversal)
following RULES.md across all 6 pairs on development data.

Idea #4 Rule:
  - Long  : candle sweeps an active major swing low (left=10, right=10) AND closes above value_area_low
  - Short : candle sweeps an active major swing high (left=10, right=10) AND closes below value_area_high
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
from app.market_analyzer.liquidity import liquidity_levels
from app.market_analyzer.volatility import atr
from app.market_analyzer.volume_profile import value_area, volume_profile

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY"]
TIMEFRAME = "M15"
HORIZON = 8
PROFILE_WINDOW = 200
VALUE_SHARE = 0.70
SWING_SIZE = 10
K = 4


def get_bin_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def generate_signals_for_pair(symbol: str, candles: pd.DataFrame) -> pd.Series:
    bin_size = get_bin_size(symbol)
    n = len(candles)
    signals = np.zeros(n, dtype=int)
    closes = candles["close"].to_numpy(dtype=float)

    levels = liquidity_levels(candles, left=SWING_SIZE, right=SWING_SIZE)
    valid = levels[levels["swept_at"].notna() & (levels["known_at"] <= levels["swept_at"])]
    low_sweeps = set(valid[valid["kind"] == "swing_low"]["swept_at"])
    high_sweeps = set(valid[valid["kind"] == "swing_high"]["swept_at"])

    swept_candles = sorted(list(low_sweeps | high_sweeps))
    valid_candidates = [i for i in swept_candles if i >= PROFILE_WINDOW and i < n - HORIZON]

    for i in valid_candidates:
        is_low_sweep = i in low_sweeps
        is_high_sweep = i in high_sweeps
        if is_low_sweep and is_high_sweep:
            continue

        start = i - PROFILE_WINDOW + 1
        recent = candles.iloc[start : i + 1]
        prof = volume_profile(recent, bin_size)
        area = value_area(prof, VALUE_SHARE)
        if area is None:
            continue
        val, vah = area

        if is_low_sweep and closes[i] > val:
            signals[i] = 1
        elif is_high_sweep and closes[i] < vah:
            signals[i] = -1

    return pd.Series(signals, index=candles.index)


def main():
    print(f"============================================================")
    print(f"Running Idea #4 Evaluation: Major Structural Failed Auction (k={K})")
    print(f"Pairs: {', '.join(PAIRS)} | Swing: left={SWING_SIZE}, right={SWING_SIZE} | Horizon: {HORIZON}")
    print(f"============================================================\n")

    all_trades_list = []
    t_start = time.time()

    for symbol in PAIRS:
        t0 = time.time()
        print(f"Loading {symbol}...", end=" ", flush=True)
        candles = load_candles(symbol, TIMEFRAME, part="development")
        atr_vals = atr(candles, 14)
        print(f"{len(candles):,} candles. Signals...", end=" ", flush=True)

        signals = generate_signals_for_pair(symbol, candles)
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
