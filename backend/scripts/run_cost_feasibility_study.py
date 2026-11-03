"""
run_cost_feasibility_study.py
-----------------------------
Measures cost feasibility for M15, H1, and H4 timeframes:
  1. Timeframe ATR(14)
  2. Fee in ATR units (average and worst-case)
  3. Typical absolute price move for holding times h in [4, 8, 12] (median and mean in ATR)
  4. Ratio of typical move to fee
  5. Break-even bar (% of typical move required to break even)
  6. Possible non-overlapping trade count (vs 300 minimum)
  7. Hourly spread pattern (server & UTC hours)
  8. Ranking of cheapest pairs by fee
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.loader import load_candles
from app.evaluation.outcomes import point_size
from app.evaluation.resample import resample_m15
from app.market_analyzer.volatility import atr

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY"]
HOLDINGS = [4, 8, 12]


def analyze_timeframe(symbol: str, candles: pd.DataFrame, tf_name: str, step_minutes: int):
    point = point_size(symbol)
    atr_series = atr(candles, 14)
    atr_vals = atr_series.to_numpy(dtype=float)

    opens = candles["open"].to_numpy(dtype=float)
    closes = candles["close"].to_numpy(dtype=float)
    times = candles["time"].to_numpy()

    if "spread_avg" in candles.columns:
        spreads_avg = candles["spread_avg"].to_numpy(dtype=float)
        spreads_worst = candles["spread_worst"].to_numpy(dtype=float)
    else:
        spreads_avg = candles["spread"].to_numpy(dtype=float)
        spreads_worst = candles["spread"].to_numpy(dtype=float)

    valid_atr_mask = (atr_vals > 0) & (~np.isnan(atr_vals))
    mean_atr = float(np.mean(atr_vals[valid_atr_mask]))

    # Fees in ATR units
    fee_avg_series = (spreads_avg * point) / atr_vals
    fee_worst_series = (spreads_worst * point) / atr_vals

    mean_fee_avg = float(np.nanmean(fee_avg_series[valid_atr_mask]))
    mean_fee_worst = float(np.nanmean(fee_worst_series[valid_atr_mask]))

    n = len(candles)
    step = np.timedelta64(step_minutes, "m")

    typical_moves = {}
    possible_counts = {}

    for h in HOLDINGS:
        moves_atr = []
        free_from = 0
        non_overlap_count = 0

        for i in range(n - h - 1):
            entry = i + 1
            exit_ = i + h
            if exit_ >= n:
                break
            if not (atr_vals[i] > 0):
                continue
            # Check back-to-back continuity (no gaps)
            if times[exit_] - times[i] != h * step:
                continue

            abs_move_atr = abs(closes[exit_] - opens[entry]) / atr_vals[i]
            moves_atr.append(abs_move_atr)

            if entry >= free_from:
                non_overlap_count += 1
                free_from = exit_ + 1

        moves_arr = np.array(moves_atr) if moves_atr else np.array([0.0])
        med_move = float(np.median(moves_arr))
        avg_move = float(np.mean(moves_arr))

        typical_moves[h] = {
            "median": med_move,
            "mean": avg_move,
            "ratio_avg": avg_move / mean_fee_avg if mean_fee_avg > 0 else 0.0,
            "ratio_worst": avg_move / mean_fee_worst if mean_fee_worst > 0 else 0.0,
            "breakeven_pct": (mean_fee_avg / avg_move * 100) if avg_move > 0 else 0.0,
        }
        possible_counts[h] = non_overlap_count

    return {
        "symbol": symbol,
        "timeframe": tf_name,
        "candles_count": n,
        "mean_atr": mean_atr,
        "mean_fee_avg": mean_fee_avg,
        "mean_fee_worst": mean_fee_worst,
        "typical_moves": typical_moves,
        "possible_counts": possible_counts,
    }


def analyze_hourly_spreads(symbol: str, candles_m15: pd.DataFrame):
    """
    Computes spread in points by hour of the day.
    Server time is EET (UTC+2 in winter, UTC+3 in summer).
    We report both Server Hour and approximate UTC Hour (Server - 2).
    """
    df = candles_m15.copy()
    df["server_hour"] = df["time"].dt.hour
    df["utc_hour"] = (df["server_hour"] - 2) % 24
    hourly = df.groupby(["server_hour", "utc_hour"])["spread"].mean().reset_index()
    return hourly


def main():
    print("==================================================================")
    print("COST FEASIBILITY STUDY: M15 vs H1 vs H4 (Development Data Only)")
    print("==================================================================\n")

    tf_configs = [
        ("M15", 15),
        ("H1", 60),
        ("H4", 240),
    ]

    all_results = []
    dropped_info = {"H1": {}, "H4": {}}
    hourly_spreads = {}

    for sym in PAIRS:
        print(f"Loading {sym} M15...", end=" ", flush=True)
        m15_candles = load_candles(sym, "M15")
        h1_candles, d_h1 = resample_m15(m15_candles, "H1")
        h4_candles, d_h4 = resample_m15(m15_candles, "H4")
        dropped_info["H1"][sym] = d_h1
        dropped_info["H4"][sym] = d_h4

        hourly_spreads[sym] = analyze_hourly_spreads(sym, m15_candles)

        res_m15 = analyze_timeframe(sym, m15_candles, "M15", 15)
        res_h1 = analyze_timeframe(sym, h1_candles, "H1", 60)
        res_h4 = analyze_timeframe(sym, h4_candles, "H4", 240)

        all_results.extend([res_m15, res_h1, res_h4])
        print(f"Done. (H1 dropped: {d_h1}, H4 dropped: {d_h4})")

    # Aggregate summaries across all pairs
    df_res = pd.DataFrame(all_results)

    print("\n" + "=" * 65)
    print("SECTION 2: RESAMPLING AND DROPPED CANDLE REPORT")
    print("=" * 65)
    for tf in ["H1", "H4"]:
        total_dropped = sum(dropped_info[tf].values())
        print(f"{tf}: Total dropped across all 6 pairs = {total_dropped} incomplete candles.")
        print(f"    Per-pair dropped: {dropped_info[tf]}")

    print("\n" + "=" * 65)
    print("SECTION 3: TIMEFRAME COMPARISON TABLE (ALL PAIRS AVERAGE)")
    print("=" * 65)

    for tf in ["M15", "H1", "H4"]:
        sub = [r for r in all_results if r["timeframe"] == tf]
        avg_candles = np.mean([r["candles_count"] for r in sub])
        avg_fee_avg = np.mean([r["mean_fee_avg"] for r in sub])
        avg_fee_worst = np.mean([r["mean_fee_worst"] for r in sub])

        print(f"\n--- TIMEFRAME: {tf} ---")
        print(f"Average Candles / Pair : {avg_candles:,.0f}")
        print(f"Average Fee (Spread/ATR): {avg_fee_avg:.4f} ATR (Average Spread) | {avg_fee_worst:.4f} ATR (Worst Spread)")

        for h in HOLDINGS:
            avg_move_mean = np.mean([r["typical_moves"][h]["mean"] for r in sub])
            avg_move_med = np.mean([r["typical_moves"][h]["median"] for r in sub])
            ratio = np.mean([r["typical_moves"][h]["ratio_avg"] for r in sub])
            be_pct = np.mean([r["typical_moves"][h]["breakeven_pct"] for r in sub])
            possible_n = np.mean([r["possible_counts"][h] for r in sub])
            tot_possible_n = sum(r["possible_counts"][h] for r in sub)

            print(f"  Hold {h:>2} candles: Typical Move = {avg_move_mean:.3f} ATR (med {avg_move_med:.3f}) | "
                  f"Ratio = {ratio:.1f}x | Break-even = {be_pct:.1f}% of move | "
                  f"Possible Trades = {possible_n:,.0f}/pair ({tot_possible_n:,.0f} total)")

    print("\n" + "=" * 65)
    print("CHEAPEST PAIRS RANKING (BY FEE IN ATR)")
    print("=" * 65)
    for tf in ["M15", "H1", "H4"]:
        sub = [r for r in all_results if r["timeframe"] == tf]
        sorted_sub = sorted(sub, key=lambda x: x["mean_fee_avg"])
        rank_str = ", ".join([f"{r['symbol']} ({r['mean_fee_avg']:.4f} ATR)" for r in sorted_sub])
        print(f"{tf:<4} ranking : {rank_str}")

    print("\n" + "=" * 65)
    print("SPREAD BY HOUR OF DAY (CHEAPEST & WIDEST HOURS)")
    print("=" * 65)
    for sym in PAIRS:
        h_df = hourly_spreads[sym].sort_values("spread")
        cheapest_3 = h_df.head(3)
        widest_3 = h_df.tail(3)

        cheap_str = ", ".join([f"{int(r.utc_hour):02d}:00 UTC ({r.spread:.1f} pts)" for _, r in cheapest_3.iterrows()])
        wide_str = ", ".join([f"{int(r.utc_hour):02d}:00 UTC ({r.spread:.1f} pts)" for _, r in widest_3.iterrows()])
        print(f"{sym:<7} | Cheapest: {cheap_str} | Widest: {wide_str}")

    print("=" * 65)


if __name__ == "__main__":
    main()
