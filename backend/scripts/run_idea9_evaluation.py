"""
run_idea9_evaluation.py
-----------------------
Official evaluation for Idea #9:
  "The 24-Hour False Breakout Trap with Trampoline & Toll Guards on H1"

Hypothesis:
  When price breaks above the 24-hour high or below the 24-hour low and gets
  rejected back inside during elastic regime (rho < 0) and outside rollover hours,
  trapped breakout orders fuel a mean-reverting snapback that beats the broker spread.

Settings:
  - Timeframe: H1 (resampled from M15 complete candles)
  - Pairs: EURUSD, GBPUSD, USDCHF, USDCAD, EURJPY (liquid 5-pair portfolio)
  - Lookback: 24 (24 hours)
  - Fixed Horizon: 8 bars (standard RULES.md protocol)
  - Dynamic Exit: Equilibrium (z=0), 1.5x ATR Stop Loss, 16-bar Time Limit
  - k = 9
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.loader import load_candles
from app.entry.entry_rules import generate_trap_signals
from app.evaluation.edge_stats import evaluate_edge, format_report
from app.evaluation.outcomes import point_size
from app.evaluation.resample import resample_m15
from app.exit.exit_rules import check_trade_exit
from app.market_analyzer.math_analyzer import rolling_statistics
from app.market_analyzer.volatility import atr

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "EURJPY"]
HORIZON = 8
LOOKBACK = 24
K = 9


def build_h1_fixed_trades(
    symbol: str,
    candles: pd.DataFrame,
    signals: pd.Series,
    atr_vals: pd.Series,
    horizon: int = 8,
) -> pd.DataFrame:
    """Builds standard RULES.md fixed-horizon trades."""
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
    busy_until = 0

    for i in np.flatnonzero(sig != 0):
        entry = i + 1
        exit_ = entry + horizon - 1

        if exit_ >= n:
            break
        if entry < busy_until:
            continue
        if not atr_arr[i] > 0:
            continue
        # Verify continuous back-to-back candles (no weekend jump)
        if times[exit_] - times[entry] != (horizon - 1) * step:
            continue

        direction = int(sig[i])
        move_atr = (closes[exit_] - opens[entry]) / atr_arr[i]
        cost_atr = spreads[entry] * point / atr_arr[i]
        outcome_atr = direction * move_atr

        t_dt = pd.Timestamp(times[entry])
        rows.append(
            {
                "symbol": symbol,
                "signal_pos": i,
                "entry_time": t_dt,
                "direction": direction,
                "move_atr": float(move_atr),
                "outcome_atr": float(outcome_atr),
                "cost_atr": float(cost_atr),
                "net_atr": float(outcome_atr - cost_atr),
                "week": int(t_dt.isocalendar().week),
                "quarter": f"{t_dt.year}Q{t_dt.quarter}",
            }
        )
        busy_until = exit_ + 1

    return pd.DataFrame(rows)


def build_h1_dynamic_trades(
    symbol: str,
    candles: pd.DataFrame,
    signals: pd.Series,
    atr_vals: pd.Series,
    z_scores: pd.Series,
    stop_loss_atr: float = 1.5,
    max_bars: int = 16,
) -> pd.DataFrame:
    """Builds dynamic-exit trades using target equilibrium, stop loss, and time limit."""
    n = len(candles)
    sig = signals.to_numpy()
    atr_arr = atr_vals.to_numpy(dtype=float)
    z_arr = z_scores.to_numpy(dtype=float)
    times = candles["time"].to_numpy()
    opens = candles["open"].to_numpy(dtype=float)
    spreads = candles["spread"].to_numpy(dtype=float)

    point = point_size(symbol)
    step = np.timedelta64(1, "h")

    rows = []
    busy_until = 0

    for i in np.flatnonzero(sig != 0):
        entry = i + 1
        if entry >= n:
            break
        if entry < busy_until:
            continue
        if not atr_arr[i] > 0:
            continue

        direction = int(sig[i])
        entry_price = opens[entry]
        cost_atr = spreads[entry] * point / atr_arr[i]

        # Step forward bar-by-bar to find dynamic exit
        exit_pos = None
        exit_price = None
        exit_reason = None

        for bar_idx in range(entry, min(n, entry + max_bars + 1)):
            # Check continuous time
            bars_held = bar_idx - entry
            if times[bar_idx] - times[entry] != bars_held * step:
                # Crossed gap/weekend, exit at open
                exit_pos = bar_idx
                exit_price = opens[bar_idx]
                exit_reason = "gap_exit"
                break

            candle_series = candles.iloc[bar_idx]
            decision = check_trade_exit(
                direction=direction,
                entry_price=entry_price,
                current_candle=candle_series,
                current_z_score=z_arr[bar_idx],
                current_atr=atr_arr[i],
                bars_held=bars_held,
                stop_loss_atr=stop_loss_atr,
                max_bars=max_bars,
            )

            if decision is not None:
                exit_pos = bar_idx
                exit_price = decision.exit_price
                exit_reason = decision.exit_reason
                break

        if exit_pos is None:
            continue

        move_atr = (exit_price - entry_price) / atr_arr[i]
        outcome_atr = direction * move_atr

        t_dt = pd.Timestamp(times[entry])
        rows.append(
            {
                "symbol": symbol,
                "signal_pos": i,
                "entry_time": t_dt,
                "direction": direction,
                "bars_held": exit_pos - entry,
                "exit_reason": exit_reason,
                "move_atr": float(move_atr),
                "outcome_atr": float(outcome_atr),
                "cost_atr": float(cost_atr),
                "net_atr": float(outcome_atr - cost_atr),
                "week": int(t_dt.isocalendar().week),
                "quarter": f"{t_dt.year}Q{t_dt.quarter}",
            }
        )
        busy_until = exit_pos + 1

    return pd.DataFrame(rows)


def main():
    print("==================================================================")
    print(f"OFFICIAL EVALUATION FOR IDEA #9 (k={K})")
    print(f"Pairs: {', '.join(PAIRS)} | Timeframe: H1 | Lookback: {LOOKBACK}")
    print("==================================================================\n")

    fixed_trades_list = []
    dynamic_trades_list = []

    for symbol in PAIRS:
        print(f"Loading & Resampling {symbol}...", end=" ", flush=True)
        raw_m15 = load_candles(symbol, "M15", part="development")
        candles_h1, dropped = resample_m15(raw_m15, "H1")
        print(f"{len(candles_h1):,} H1 candles (dropped {dropped}). Signals...", end=" ", flush=True)

        atr_vals = atr(candles_h1, period=14)
        _, _, z_scores = rolling_statistics(candles_h1["close"], window=LOOKBACK)

        signals = generate_trap_signals(candles_h1, symbol=symbol, lookback=LOOKBACK, max_cost_ratio=0.15)
        sig_count = (signals != 0).sum()

        fixed_trades = build_h1_fixed_trades(symbol, candles_h1, signals, atr_vals, horizon=HORIZON)
        dynamic_trades = build_h1_dynamic_trades(symbol, candles_h1, signals, atr_vals, z_scores)

        fixed_trades_list.append(fixed_trades)
        dynamic_trades_list.append(dynamic_trades)

        fx_net = fixed_trades["net_atr"].mean() if len(fixed_trades) > 0 else 0.0
        dyn_net = dynamic_trades["net_atr"].mean() if len(dynamic_trades) > 0 else 0.0
        print(f"{sig_count:,} sigs | Fixed 8h: {len(fixed_trades)} trades (Net: {fx_net:+.4f} ATR) | Dynamic: {len(dynamic_trades)} trades (Net: {dyn_net:+.4f} ATR)")

    all_fixed = pd.concat(fixed_trades_list, ignore_index=True)
    all_dynamic = pd.concat(dynamic_trades_list, ignore_index=True)

    print("\n" + "=" * 60)
    print("OFFICIAL RULES.md EVALUATION (Fixed 8-Hour Holding)")
    print("=" * 60)
    report_fixed = evaluate_edge(all_fixed, k=K, seed=0)
    print(format_report(report_fixed))

    print("\n" + "=" * 60)
    print("DYNAMIC EXIT EVALUATION (Target Equilibrium + Stop Loss + Time Limit)")
    print("=" * 60)
    report_dyn = evaluate_edge(all_dynamic, k=K, seed=0)
    print(format_report(report_dyn))

    print("\n" + "=" * 60)
    print("DYNAMIC EXIT BREAKDOWN BY REASON")
    print("=" * 60)
    for reason, grp in all_dynamic.groupby("exit_reason"):
        win_rate = (grp["net_atr"] > 0).mean() * 100
        print(f"  {reason:<20}: {len(grp):>4} trades ({len(grp)/len(all_dynamic)*100:>5.1f}%) | Mean Net: {grp['net_atr'].mean():>+7.4f} ATR | Win: {win_rate:>5.1f}%")

    print("\nPER-PAIR NET OUTCOMES (Dynamic):")
    for symbol, grp in all_dynamic.groupby("symbol"):
        win_rate = (grp["net_atr"] > 0).mean() * 100
        print(f"  {symbol}: {len(grp):>4} trades | Mean Gross: {grp['outcome_atr'].mean():>+7.4f} ATR | Cost: {grp['cost_atr'].mean():>6.4f} ATR | Net: {grp['net_atr'].mean():>+7.4f} ATR | Win: {win_rate:>5.1f}%")


if __name__ == "__main__":
    main()
