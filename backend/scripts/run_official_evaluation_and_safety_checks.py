"""
run_official_evaluation_and_safety_checks.py
---------------------------------------------
Performs the complete official evaluation for Idea #7:
  - Step 2: Tests A, B, C, D, E across each pair and all pairs combined
  - Step 3: Safety Checks (Random, Quarters, +30% Cost, 1-Candle Delay, Pairs, Trade Count, 5-Outliers)
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.loader import load_candles
from app.entry.entry_rules import generate_mean_reversion_signals
from app.evaluation.edge_stats import (
    evaluate_edge,
    format_report,
    interval_confidence,
    random_direction_beat_fraction,
    random_runs_for,
    repeat_check,
    required_beat_fraction,
    weekly_bootstrap_interval,
)
from app.evaluation.outcomes import build_trades, point_size
from app.market_analyzer.volatility import atr

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY"]
TIMEFRAME = "M15"
HORIZON = 8
K = 7


def run_delayed_trades(symbol: str, candles: pd.DataFrame, signals: pd.Series, atr_vals: pd.Series) -> pd.DataFrame:
    """
    Simulates a 1-candle entry delay (entry at i + 2 instead of i + 1, hold for 8 candles to i + 10).
    """
    n = len(candles)
    sig = signals.to_numpy()
    atr_arr = atr_vals.to_numpy(dtype=float)
    times = candles["time"].to_numpy()
    opens = candles["open"].to_numpy(dtype=float)
    closes = candles["close"].to_numpy(dtype=float)
    spreads = candles["spread"].to_numpy(dtype=float)

    point = point_size(symbol)
    step = np.timedelta64(15, "m")

    rows = []
    free_from = 0

    for i in np.flatnonzero(sig != 0):
        entry = i + 2  # Delayed by 1 candle!
        exit_ = entry + HORIZON - 1  # 8 candles held

        if exit_ >= n:
            break
        if entry < free_from:
            continue
        if not atr_arr[i] > 0:
            continue
        if times[exit_] - times[entry] != (HORIZON - 1) * step:
            continue

        direction = int(sig[i])
        move = (closes[exit_] - opens[entry]) / atr_arr[i]
        cost = spreads[entry] * point / atr_arr[i]

        rows.append(
            {
                "symbol": symbol,
                "direction": direction,
                "move_atr": float(move),
                "outcome_atr": float(direction * move),
                "cost_atr": float(cost),
                "net_atr": float(direction * move - cost),
            }
        )
        free_from = exit_ + 1

    return pd.DataFrame(rows)


def main():
    print("==================================================================")
    print(f"OFFICIAL MODEL EVALUATION & EXTRA SAFETY CHECKS (k={K})")
    print("==================================================================\n")

    per_pair_trades = {}
    per_pair_reports = {}
    delayed_trades_list = []

    for sym in PAIRS:
        candles = load_candles(sym, TIMEFRAME)
        atr_vals = atr(candles, 14)
        signals = generate_mean_reversion_signals(candles, sym)

        trades = build_trades(sym, candles, signals, atr_vals, horizon=HORIZON)
        trades["net_atr"] = trades["outcome_atr"] - trades["cost_atr"]
        per_pair_trades[sym] = trades
        per_pair_reports[sym] = evaluate_edge(trades, k=K, seed=0)

        # Build delayed trades for Safety Check d
        delayed_df = run_delayed_trades(sym, candles, signals, atr_vals)
        delayed_trades_list.append(delayed_df)

    combined_trades = pd.concat(per_pair_trades.values(), ignore_index=True)
    combined_report = evaluate_edge(combined_trades, k=K, seed=0)

    # -------------------------------------------------------------
    # STEP 2: OFFICIAL RESULTS TABLE
    # -------------------------------------------------------------
    print("STEP 2 - OFFICIAL TESTS A, B, C, D, E TABLE\n")
    print(f"{'Pair':<10} | {'Trades':<7} | {'Gross ATR':<10} | {'Cost ATR':<9} | {'Net ATR':<9} | {'A':<5} | {'B':<5} | {'C':<5} | {'D':<5} | {'E':<5}")
    print("-" * 85)

    for sym in PAIRS:
        t = per_pair_trades[sym]
        r = per_pair_reports[sym]
        n_tr = len(t)
        if n_tr > 0:
            mo = t["outcome_atr"].mean()
            mc = t["cost_atr"].mean()
            net = mo - mc
            p_a = "PASS" if r.passed["A"] else "FAIL"
            p_b = "PASS" if r.passed["B"] else "FAIL"
            p_c = "PASS" if r.passed["C"] else "FAIL"
            p_d = "PASS" if r.passed["D"] else "FAIL"
            p_e = "PASS" if r.passed["E"] else "FAIL"
            print(f"{sym:<10} | {n_tr:<7} | {mo:+10.4f} | {mc:9.4f} | {net:+9.4f} | {p_a:<5} | {p_b:<5} | {p_c:<5} | {p_d:<5} | {p_e:<5}")
        else:
            print(f"{sym:<10} | 0       |        N/A |       N/A |       N/A | FAIL  | FAIL  | FAIL  | FAIL  | FAIL ")

    print("-" * 85)
    tot_trades = len(combined_trades)
    tot_mo = combined_trades["outcome_atr"].mean()
    tot_mc = combined_trades["cost_atr"].mean()
    tot_net = tot_mo - tot_mc
    p_a = "PASS" if combined_report.passed["A"] else "FAIL"
    p_b = "PASS" if combined_report.passed["B"] else "FAIL"
    p_c = "PASS" if combined_report.passed["C"] else "FAIL"
    p_d = "PASS" if combined_report.passed["D"] else "FAIL"
    p_e = "PASS" if combined_report.passed["E"] else "FAIL"
    print(f"{'ALL PAIRS':<10} | {tot_trades:<7} | {tot_mo:+10.4f} | {tot_mc:9.4f} | {tot_net:+9.4f} | {p_a:<5} | {p_b:<5} | {p_c:<5} | {p_d:<5} | {p_e:<5}")
    print("-" * 85)

    # -------------------------------------------------------------
    # STEP 3: EXTRA SAFETY CHECKS
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("STEP 3 - EXTRA SAFETY CHECKS")
    print("=" * 65)

    # a) Random check
    beat_frac = combined_report.beat_fraction
    req_frac = required_beat_fraction(K)
    print(f"a) Random Check      : Beat {beat_frac*100:.1f}% of 1,000 random runs (Needed {req_frac*100:.1f}%). {'PASS' if beat_frac >= req_frac else 'FAIL'}")

    # b) Time check (Quarterly)
    q_grouped = combined_trades.groupby("quarter")["net_atr"].mean()
    total_q = len(q_grouped)
    pos_q = (q_grouped > 0).sum()
    q_pct = (pos_q / total_q) * 100 if total_q > 0 else 0
    print(f"b) Time Check        : {pos_q}/{total_q} quarters profitable ({q_pct:.1f}%). {'PASS' if q_pct >= 70 else 'FAIL'}")
    print(f"   Quarterly details : {dict(q_grouped.round(4))}")

    # c) Cost check (+30% spread)
    cost_stressed_net = tot_mo - (1.30 * tot_mc)
    print(f"c) Cost Check (+30%) : Net outcome under 1.3x spread is {cost_stressed_net:+.4f} ATR. {'PASS' if cost_stressed_net > 0 else 'FAIL'}")

    # d) Delay check (+1 candle)
    all_delayed = pd.concat(delayed_trades_list, ignore_index=True)
    delay_net = all_delayed["net_atr"].mean()
    print(f"d) Delay Check (+1)  : Net outcome with 1-candle delay is {delay_net:+.4f} ATR. {'PASS' if delay_net > 0 else 'FAIL'}")

    # e) Pair check
    pairs_pos_net = sum(per_pair_trades[s]["net_atr"].mean() > 0 for s in PAIRS)
    pairs_pos_gross = sum(per_pair_trades[s]["outcome_atr"].mean() > 0 for s in PAIRS)
    print(f"e) Pair Check        : {pairs_pos_gross}/6 pairs positive gross. {pairs_pos_net}/6 pairs positive net after spread.")

    # f) Trade count check
    print(f"f) Trade Count Check : {tot_trades:,} total trades (Minimum required: 300). {'PASS' if tot_trades >= 300 else 'FAIL'}")

    # g) Outlier check (remove top 5 best trades)
    top_5_dropped = combined_trades.sort_values("net_atr", ascending=False).iloc[5:]
    outlier_net = top_5_dropped["net_atr"].mean()
    print(f"g) Outlier Check     : Net outcome after removing top 5 best trades is {outlier_net:+.4f} ATR. {'PASS' if outlier_net > 0 else 'FAIL'}")
    print("=" * 65)


if __name__ == "__main__":
    main()
