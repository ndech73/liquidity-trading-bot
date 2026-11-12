"""
run_idea9_h4_evaluation.py
--------------------------
Evaluates Idea #9 on the 4-Hour (H4) timeframe:
  - Timeframe: H4 (resampled from complete M15 candles)
  - Pairs: EURUSD, GBPUSD, USDCHF, USDCAD, EURJPY
  - Lookback: 6 (6 x 4h = 24 hours)
  - Fixed Horizon: 4 bars (16 hours) and 6 bars (24 hours)
  - Dynamic Exit: Target Equilibrium (z=0), 1.5x ATR Stop, 6-bar Time Limit
"""

import sys
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
LOOKBACK = 6  # 6 x 4h = 24 hours
K = 9


def build_h4_dynamic_trades(
    symbol: str,
    candles: pd.DataFrame,
    signals: pd.Series,
    atr_vals: pd.Series,
    z_scores: pd.Series,
    stop_loss_atr: float = 1.5,
    max_bars: int = 6,
) -> pd.DataFrame:
    n = len(candles)
    sig = signals.to_numpy()
    atr_arr = atr_vals.to_numpy(dtype=float)
    z_arr = z_scores.to_numpy(dtype=float)
    times = candles["time"].to_numpy()
    opens = candles["open"].to_numpy(dtype=float)
    spreads = candles["spread"].to_numpy(dtype=float)

    point = point_size(symbol)
    step = np.timedelta64(4, "h")

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

        exit_pos = None
        exit_price = None
        exit_reason = None

        for bar_idx in range(entry, min(n, entry + max_bars + 1)):
            bars_held = bar_idx - entry
            if times[bar_idx] - times[entry] != bars_held * step:
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
    print(f"EVALUATION ON 4-HOUR (H4) TIMEFRAME")
    print(f"Pairs: {', '.join(PAIRS)} | Lookback: {LOOKBACK} (24h) | Max Hold: 6 bars (24h)")
    print("==================================================================\n")

    trades_list = []

    for symbol in PAIRS:
        raw_m15 = load_candles(symbol, "M15", part="development")
        candles_h4, dropped = resample_m15(raw_m15, "H4")

        atr_vals = atr(candles_h4, period=14)
        _, _, z_scores = rolling_statistics(candles_h4["close"], window=LOOKBACK)

        signals = generate_trap_signals(candles_h4, symbol=symbol, lookback=LOOKBACK, max_cost_ratio=0.15)
        trades = build_h4_dynamic_trades(symbol, candles_h4, signals, atr_vals, z_scores)
        trades_list.append(trades)

        net_atr = trades["net_atr"].mean() if len(trades) > 0 else 0.0
        win_rate = (trades["net_atr"] > 0).mean() * 100 if len(trades) > 0 else 0.0
        print(f"  {symbol}: {len(trades)} trades | Net: {net_atr:>+7.4f} ATR | Win: {win_rate:>5.1f}%")

    all_trades = pd.concat(trades_list, ignore_index=True)

    print("\n" + "=" * 60)
    print("H4 STATISTICAL REPORT")
    print("=" * 60)
    report = evaluate_edge(all_trades, k=K, seed=0)
    print(format_report(report))


if __name__ == "__main__":
    main()
