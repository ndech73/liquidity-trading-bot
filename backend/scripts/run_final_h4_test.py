"""
run_final_h4_test.py
--------------------
The official final evaluation of the H4 false-breakout trading model
under RULES_v2.md (k=12).
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.data.loader import load_candles
from app.entry.entry_rules import generate_trap_signals
from app.evaluation.final_sim import simulate_pair
from app.evaluation.final_stats import final_report
from app.evaluation.resample import resample_m15
from app.market_analyzer.math_analyzer import rolling_statistics
from app.market_analyzer.volatility import atr

K = 12
LOOKBACK = 6
PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY"]
TIMEFRAME = "H4"


class TeeLogger:
    """Captures and mirrors output to both stdout and a report file."""

    def __init__(self, filepath: Path):
        self.terminal = sys.stdout
        self.log_file = open(filepath, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()


def main():
    report_file = BACKEND / "final_h4_report.txt"
    tee = TeeLogger(report_file)
    sys.stdout = tee

    try:
        print("=" * 70)
        print("FINAL TEST OF THE H4 FALSE-BREAKOUT MODEL (RULES_v2.md, k=12)")
        print("=" * 70)

        # Pre-check: Holdout access log lines before loading
        holdout_log_path = BACKEND / "data_files" / "holdout_access.log"
        lines_before = len(holdout_log_path.read_text().splitlines()) if holdout_log_path.exists() else 0

        pair_trades_dict = {}
        max_times = []

        for symbol in PAIRS:
            # Default load_candles() is locked strictly to development data
            raw_m15 = load_candles(symbol, "M15")
            candles_h4, dropped = resample_m15(raw_m15, TIMEFRAME)
            max_times.append(candles_h4["time"].max())

            atr_vals = atr(candles_h4, period=14)
            _, _, z_scores = rolling_statistics(candles_h4["close"], window=LOOKBACK)
            signals = generate_trap_signals(candles_h4, symbol=symbol, lookback=LOOKBACK, max_cost_ratio=0.15)

            df_trades = simulate_pair(
                symbol=symbol,
                candles_h4=candles_h4,
                signals=signals,
                atr_vals=atr_vals,
                z_scores=z_scores,
                stop_loss_atr=1.5,
                max_bars=6,
            )
            pair_trades_dict[symbol] = df_trades

        lines_after = len(holdout_log_path.read_text().splitlines()) if holdout_log_path.exists() else 0
        all_trades = pd.concat(list(pair_trades_dict.values()), ignore_index=True)

        # -------------------------------------------------------------
        # Section 6 Validation Checks
        # -------------------------------------------------------------
        print("\n--- SECTION 6 VALIDATION CHECKS ---")
        check1_pass = all(t < pd.Timestamp("2025-09-14") for t in max_times)
        latest_time = max(max_times) if max_times else "None"
        print(f"Check 1 (Last candle < 2025-09-14)          : {'PASS' if check1_pass else 'FAIL'} (Latest candle: {latest_time})")

        check2_pass = (lines_before == lines_after)
        print(f"Check 2 (holdout_access.log unchanged)      : {'PASS' if check2_pass else 'FAIL'} ({lines_before} -> {lines_after} lines)")

        check3_pass = all(len(pair_trades_dict[sym]) > 0 for sym in PAIRS)
        print(f"Check 3 (All 6 pairs have trades)           : {'PASS' if check3_pass else 'FAIL'}")

        # Check 4: No overlapping trades per pair
        overlapping_count = 0
        for sym, df_p in pair_trades_dict.items():
            if len(df_p) > 1:
                entries = df_p["entry_pos"].to_numpy()
                bars = df_p["bars_held"].to_numpy()
                exit_positions = entries + bars
                for idx in range(len(entries) - 1):
                    if entries[idx + 1] <= exit_positions[idx]:
                        overlapping_count += 1
        check4_pass = (overlapping_count == 0)
        print(f"Check 4 (No overlapping trades per pair)    : {'PASS' if check4_pass else 'FAIL'} (Overlaps: {overlapping_count})")

        # Check 5: Every entry_pos == signal_pos + 1
        entry_is_sig_plus_one = (all_trades["entry_pos"] == all_trades["signal_pos"] + 1).all() if len(all_trades) > 0 else False
        check5_pass = bool(entry_is_sig_plus_one)
        print(f"Check 5 (Every entry_pos == signal_pos + 1) : {'PASS' if check5_pass else 'FAIL'}")

        all_checks_passed = check1_pass and check2_pass and check3_pass and check4_pass and check5_pass

        if not all_checks_passed:
            print("\nINVALID RUN: One or more validation checks failed.")
            sys.exit(1)

        print("\nALL SECTION 6 CHECKS PASSED. RUN IS VALID.")

        # -------------------------------------------------------------
        # Per-Pair Performance Table
        # -------------------------------------------------------------
        print("\n" + "=" * 70)
        print("PER-PAIR PERFORMANCE TABLE")
        print(f"{'Pair':8s} {'Trades':7s} {'Gross (ATR)':12s} {'Cost_First':12s} {'Cost_Worst':12s} {'Net (1.25x)':12s} {'Win Rate':9s}")
        print("-" * 74)

        for sym in PAIRS:
            df_sym = pair_trades_dict[sym]
            n_t = len(df_sym)
            if n_t > 0:
                gross = df_sym["outcome_atr"].mean()
                c_first = df_sym["cost_first_atr"].mean()
                c_worst = df_sym["cost_worst_atr"].mean()
                net_125 = gross - 1.25 * c_first
                win_rate = (df_sym["outcome_atr"] > 0).mean() * 100
                print(
                    f"{sym:8s} {n_t:<7d} {gross:>+10.4f}  {c_first:>10.4f}  {c_worst:>10.4f}  {net_125:>+10.4f}  {win_rate:>7.1f}%"
                )
            else:
                print(f"{sym:8s} 0 trades")

        total_trades = len(all_trades)
        gross_all = all_trades["outcome_atr"].mean()
        cf_all = all_trades["cost_first_atr"].mean()
        cw_all = all_trades["cost_worst_atr"].mean()
        net_all = gross_all - 1.25 * cf_all
        wr_all = (all_trades["outcome_atr"] > 0).mean() * 100
        print("-" * 74)
        print(
            f"{'ALL 6':8s} {total_trades:<7d} {gross_all:>+10.4f}  {cf_all:>10.4f}  {cw_all:>10.4f}  {net_all:>+10.4f}  {wr_all:>7.1f}%"
        )
        print("=" * 70)

        # -------------------------------------------------------------
        # Exit Reasons Breakdown & Both-Triggered Count
        # -------------------------------------------------------------
        print("\n--- EXIT REASONS BREAKDOWN ---")
        for reason, grp in all_trades.groupby("exit_reason"):
            cnt = len(grp)
            pct = cnt / total_trades * 100
            m_gross = grp["outcome_atr"].mean()
            m_net = grp["outcome_atr"].mean() - 1.25 * grp["cost_first_atr"].mean()
            wr = (grp["outcome_atr"] > 0).mean() * 100
            print(f"  {reason:20s}: {cnt:5d} trades ({pct:4.1f}%) | Gross: {m_gross:>+7.4f} ATR | Net (1.25x): {m_net:>+7.4f} ATR | Win: {wr:4.1f}%")

        both_triggered_count = int(all_trades["both_triggered_on_exit"].sum())
        both_pct = both_triggered_count / total_trades * 100 if total_trades > 0 else 0.0
        print(f"\nBoth stop & target triggered on exit candle: {both_triggered_count} trades ({both_pct:.1f}%)")
        print("  (Note: In the flawed old order, these would have been wrongly booked as wins; here they are correctly stopped out.)")

        # Cost comparison
        cost_diff = (cw_all - cf_all) / cf_all * 100 if cf_all > 0 else 0.0
        print(f"\nCost Comparison: spread_first = {cf_all:.4f} ATR vs spread_worst = {cw_all:.4f} ATR ({cost_diff:+.1f}% difference)")

        # -------------------------------------------------------------
        # Official Final Report (Tests A to E)
        # -------------------------------------------------------------
        print("\n" + "=" * 70)
        print("OFFICIAL RULES_v2.md EVALUATION REPORT (k=12)")
        print("=" * 70)
        report = final_report(all_trades, k=K)
        print(report.report_text)
        print("=" * 70)

        # Print markdown Test Log row
        print("\n--- TEST LOG ROW (to paste into RULES_v2.md section 9) ---")
        today = "2026-11-12"
        mark = lambda name: "PASS" if report.passed[name] else "FAIL"
        notes = (
            f"k={K}, 6 pairs H4. Gross {report.mean_outcome:+.4f} ATR, cost_first {report.mean_cost_first:.4f} ATR, "
            f"margin_net {report.margin_net:+.4f} ATR. {both_triggered_count} stop-first corrections. Verdict: {report.verdict}"
        )
        row = f"| {today} | H4 false-breakout trap (24h fence, rho<0, toll guard, stop-first, spread_first) | {K} | {mark('A')} | {mark('B')} | {mark('C')} | {mark('D')} | {mark('E')} | - | {notes} |"
        print(row)
        print("----------------------------------------------------------\n")

    finally:
        sys.stdout = tee.terminal
        tee.close()


if __name__ == "__main__":
    main()
