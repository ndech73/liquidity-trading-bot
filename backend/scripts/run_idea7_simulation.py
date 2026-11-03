"""
run_idea7_simulation.py
-----------------------
Evaluates the mathematical mean-reversion strategy (Idea #7, k=7)
using entry_rules.py and exit_rules.py on development data.

Also simulates trading on a small $7.00 account using 0.01 micro-lots
to test real-world survivability and capital growth.
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
)
from app.exit.exit_rules import check_trade_exit
from app.market_analyzer.math_analyzer import rolling_statistics
from app.market_analyzer.volatility import atr

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY"]
TIMEFRAME = "M15"
K = 7
STARTING_CAPITAL = 7.00


def get_pip_info(symbol: str) -> tuple[float, float, float]:
    """
    Returns (point_size, pip_size, usd_per_pip_001_lot)
    For 0.01 lot (1,000 units):
      EURUSD: 1 pip = $0.10
      GBPUSD: 1 pip = $0.10
      USDCHF: 1 pip ~ $0.11
      USDCAD: 1 pip ~ $0.075
      NZDUSD: 1 pip = $0.10
      EURJPY: 1 pip ~ $0.07
    """
    sym = symbol.upper()
    if "JPY" in sym:
        point = 0.001
        pip = 0.01
        usd_per_pip = 0.07
    elif "CAD" in sym:
        point = 0.00001
        pip = 0.0001
        usd_per_pip = 0.075
    elif "CHF" in sym:
        point = 0.00001
        pip = 0.0001
        usd_per_pip = 0.11
    else:
        point = 0.00001
        pip = 0.0001
        usd_per_pip = 0.10

    return point, pip, usd_per_pip


def simulate_pair_trades(symbol: str, candles: pd.DataFrame) -> list[dict]:
    point, pip, usd_per_pip = get_pip_info(symbol)
    sigs = generate_mean_reversion_signals(candles, symbol).to_numpy()
    atr_vals = atr(candles, 14).to_numpy(dtype=float)
    _, _, z_scores = rolling_statistics(candles["close"], window=20)
    z_arr = z_scores.to_numpy(dtype=float)

    opens = candles["open"].to_numpy(dtype=float)
    highs = candles["high"].to_numpy(dtype=float)
    lows = candles["low"].to_numpy(dtype=float)
    closes = candles["close"].to_numpy(dtype=float)
    spreads = candles["spread"].to_numpy(dtype=float) if "spread" in candles.columns else np.zeros(len(candles))
    times = candles["time"].to_numpy()

    trades = []
    free_from = 0
    n = len(candles)

    for i in range(n - 17):
        sig = sigs[i]
        if sig == 0:
            continue
        entry_idx = i + 1
        if entry_idx < free_from:
            continue

        direction = int(sig)
        entry_price = float(opens[entry_idx])
        entry_atr = float(atr_vals[i])
        if entry_atr <= 0 or np.isnan(entry_atr):
            continue

        entry_spread_price = float(spreads[entry_idx] * point)
        exit_price = None
        exit_reason = None
        exit_idx = None

        for bar in range(1, 17):
            curr_idx = entry_idx + bar - 1
            curr_candle = pd.Series(
                {
                    "high": highs[curr_idx],
                    "low": lows[curr_idx],
                    "close": closes[curr_idx],
                }
            )
            decision = check_trade_exit(
                direction=direction,
                entry_price=entry_price,
                current_candle=curr_candle,
                current_z_score=float(z_arr[curr_idx]),
                current_atr=entry_atr,
                bars_held=bar,
                stop_loss_atr=1.5,
                max_bars=16,
            )
            if decision is not None and decision.should_exit:
                exit_price = float(decision.exit_price)
                exit_reason = decision.exit_reason
                exit_idx = curr_idx
                break

        if exit_price is not None:
            pnl_price = (exit_price - entry_price) * direction
            pnl_atr = pnl_price / entry_atr
            cost_atr = entry_spread_price / entry_atr
            net_atr = pnl_atr - cost_atr

            pnl_pips = pnl_price / pip
            cost_pips = entry_spread_price / pip
            net_pips = pnl_pips - cost_pips
            dollar_pnl = net_pips * usd_per_pip

            t_entry = pd.Timestamp(times[entry_idx])
            trades.append(
                {
                    "symbol": symbol,
                    "entry_time": t_entry,
                    "direction": direction,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "bars_held": exit_idx - entry_idx + 1,
                    "move_atr": float(pnl_price / entry_atr * direction),
                    "outcome_atr": float(pnl_atr),
                    "cost_atr": float(cost_atr),
                    "net_atr": float(net_atr),
                    "net_pips": float(net_pips),
                    "dollar_pnl": float(dollar_pnl),
                    "week": str(t_entry.to_period("W")),
                    "quarter": str(t_entry.to_period("Q")),
                }
            )
            free_from = exit_idx + 1

    return trades


def main():
    print("=" * 65)
    print(f"Running Idea #7 Evaluation & $7.00 Account Simulation (k={K})")
    print(f"Strategy: Z-Score Stretch + Direction Memory + Calculus Deceleration + Toll Guard")
    print("=" * 65 + "\n")

    all_trades_list = []
    t_start = time.time()

    for sym in PAIRS:
        t0 = time.time()
        print(f"Loading {sym}...", end=" ", flush=True)
        candles = load_candles(sym, TIMEFRAME, part="development")
        print(f"{len(candles):,} candles. Simulating...", end=" ", flush=True)
        trades = simulate_pair_trades(sym, candles)
        all_trades_list.extend(trades)
        elapsed = time.time() - t0

        df_sym = pd.DataFrame(trades)
        if len(df_sym) > 0:
            mo = df_sym["outcome_atr"].mean()
            mc = df_sym["cost_atr"].mean()
            net = df_sym["net_atr"].mean()
            wr = (df_sym["net_atr"] > 0).mean() * 100
            print(f"{len(trades):,} trades | WinRate: {wr:.1f}% | Net: {net:+.4f} ATR ({elapsed:.1f}s)")
        else:
            print(f"0 trades ({elapsed:.1f}s)")

    combined = pd.DataFrame(all_trades_list)
    total_time = time.time() - t_start
    print(f"\nAll pairs processed in {total_time:.1f}s.")
    print(f"Total trades collected: {len(combined):,}")

    # Sort all trades chronologically across pairs
    combined = combined.sort_values("entry_time").reset_index(drop=True)

    print("\n" + "=" * 65)
    print("EDGE EVALUATION REPORT (RULES.md Section 4)")
    print("=" * 65)
    report = evaluate_edge(combined, k=K, seed=0)
    print(format_report(report))
    print("=" * 65)

    # -------------------------------------------------------------
    # Simulation of the $7.00 Capital Account
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print("REALISTIC $7.00 CAPITAL SIMULATION (0.01 Micro-Lot)")
    print("=" * 65)

    balance = STARTING_CAPITAL
    peak_balance = STARTING_CAPITAL
    max_drawdown_dollar = 0.0
    busted = False
    bust_trade_idx = None
    balance_history = [balance]

    # Margin requirement for 0.01 lot at 1:500 leverage is ~$2.20
    # If balance falls below $2.00, broker triggers a stop-out (margin liquidation)
    MIN_MARGIN = 2.00

    wins = 0
    losses = 0

    for idx, row in combined.iterrows():
        pnl = row["dollar_pnl"]
        if pnl > 0:
            wins += 1
        else:
            losses += 1

        balance += pnl
        balance_history.append(balance)

        if balance > peak_balance:
            peak_balance = balance

        dd = peak_balance - balance
        if dd > max_drawdown_dollar:
            max_drawdown_dollar = dd

        if balance < MIN_MARGIN and not busted:
            busted = True
            bust_trade_idx = idx

    print(f"Starting Balance       : ${STARTING_CAPITAL:.2f}")
    print(f"Total Trades Taken     : {len(combined):,}")
    print(f"Winning Trades         : {wins:,} ({(wins/len(combined)*100):.1f}%)")
    print(f"Losing Trades          : {losses:,} ({(losses/len(combined)*100):.1f}%)")
    print(f"Peak Balance Achieved  : ${peak_balance:.2f}")
    print(f"Max Dollar Drawdown    : ${max_drawdown_dollar:.2f}")

    if busted:
        print(f"\nAccount Status         : STOPPED OUT (Margin Liquidation at trade #{bust_trade_idx})")
        print(f"Final Balance          : ${balance:.2f}")
    else:
        print(f"\nAccount Status         : SURVIVED & ACTIVE")
        print(f"Final Balance          : ${balance:.2f}")
        print(f"Total Net Return       : {((balance - STARTING_CAPITAL) / STARTING_CAPITAL * 100):+.1f}%")

    print("=" * 65)


if __name__ == "__main__":
    main()
