"""
run_idea8_evaluation.py
-----------------------
Runs the official evaluation for Idea #8:
  "On H1 candles, go long at the next candle's open if the last close is higher
   than the close 24 candles earlier. Go short if it is lower. Hold for exactly
   8 candles, then exit."

Settings:
  - Timeframe: H1 (built from complete M15 candles)
  - Pairs: EURUSD, GBPUSD, USDCHF, USDCAD, EURJPY (NZDUSD excluded due to fee)
  - Exclusion: No entries when signal candle closes at 20:00, 21:00, or 22:00 UTC
  - Holding time: 8 candles
  - k = 8
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.loader import load_candles
from app.evaluation.edge_stats import (
    evaluate_edge,
    format_report,
    random_direction_beat_fraction,
    random_runs_for,
    required_beat_fraction,
)
from app.evaluation.idea8_signals import generate_idea8_signals
from app.evaluation.outcomes import build_trades, point_size
from app.evaluation.resample import resample_m15
from app.market_analyzer.volatility import atr

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "EURJPY"]
HORIZON = 8
LOOKBACK = 24
K = 8


def run_delayed_h1_trades(symbol: str, candles: pd.DataFrame, signals: pd.Series, atr_vals: pd.Series) -> pd.DataFrame:
    n = len(candles)
    sig = signals.to_numpy()
    atr_arr = atr_vals.to_numpy(dtype=float)
    times = candles["time"].to_numpy()
    opens = candles["open"].to_numpy(dtype=float)
    closes = candles["close"].to_numpy(dtype=float)
    spreads = candles["spread"].to_numpy(dtype=float)

    point = point_size(symbol)
    step = np.timedelta64(1, "h")

    rows = []
    free_from = 0

    for i in np.flatnonzero(sig != 0):
        entry = i + 2  # Delayed entry by 1 candle
        exit_ = entry + HORIZON - 1

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
    print(f"OFFICIAL EVALUATION FOR IDEA #8 (k={K})")
    print(f"Pairs: {', '.join(PAIRS)} | Timeframe: H1 | Lookback: {LOOKBACK} | Hold: {HORIZON}")
    print("==================================================================\n")

    per_pair_trades = {}
    per_pair_reports = {}
    delayed_trades_list = []

    for sym in PAIRS:
        candles_m15 = load_candles(sym, "M15")
        candles_h1, dropped = resample_m15(candles_m15, "H1")
        atr_vals = atr(candles_h1, 14)
        signals = generate_idea8_signals(candles_h1, lookback=LOOKBACK)

        trades = build_trades(sym, candles_h1, signals, atr_vals, horizon=HORIZON, candle_minutes=60)
        trades["net_atr"] = trades["outcome_atr"] - trades["cost_atr"]
        per_pair_trades[sym] = trades
        per_pair_reports[sym] = evaluate_edge(trades, k=K, seed=0)

        delayed = run_delayed_h1_trades(sym, candles_h1, signals, atr_vals)
        delayed_trades_list.append(delayed)

    combined_trades = pd.concat(per_pair_trades.values(), ignore_index=True)
    combined_report = evaluate_edge(combined_trades, k=K, seed=0)

    # -------------------------------------------------------------
    # STEP 2: TABLE
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
    print(f"{'ALL 5 PAIRS':<10} | {tot_trades:<7} | {tot_mo:+10.4f} | {tot_mc:9.4f} | {tot_net:+9.4f} | {p_a:<5} | {p_b:<5} | {p_c:<5} | {p_d:<5} | {p_e:<5}")
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
    print(f"e) Pair Check        : {pairs_pos_gross}/{len(PAIRS)} pairs positive gross. {pairs_pos_net}/{len(PAIRS)} pairs positive net after spread.")

    # f) Trade count check
    print(f"f) Trade Count Check : {tot_trades:,} total trades (Minimum required: 300). {'PASS' if tot_trades >= 300 else 'FAIL'}")

    # g) Outlier check (remove top 5 best trades)
    top_5_dropped = combined_trades.sort_values("net_atr", ascending=False).iloc[5:]
    outlier_net = top_5_dropped["net_atr"].mean()
    print(f"g) Outlier Check     : Net outcome after removing top 5 best trades is {outlier_net:+.4f} ATR. {'PASS' if outlier_net > 0 else 'FAIL'}")

    # h) Direction check (Long vs Short)
    long_trades = combined_trades[combined_trades["direction"] == 1]
    short_trades = combined_trades[combined_trades["direction"] == -1]
    long_net = long_trades["net_atr"].mean() if len(long_trades) > 0 else 0.0
    short_net = short_trades["net_atr"].mean() if len(short_trades) > 0 else 0.0
    print(f"h) Direction Check   : Long Net = {long_net:+.4f} ATR ({len(long_trades):,} trades) | Short Net = {short_net:+.4f} ATR ({len(short_trades):,} trades)")
    print("=" * 65)


if __name__ == "__main__":
    main()
