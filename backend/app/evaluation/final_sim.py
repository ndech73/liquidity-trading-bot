"""
final_sim.py
------------
Simulates trades under RULES_v2.md on H4 timeframe:
  - Stop is checked FIRST before target.
  - If open is past stop, fill at open.
  - Gaps exit at candle open.
  - Mirrors exit path for opposite direction (outcome_atr_opposite).
  - Uses spread_first for cost.
"""

from typing import Optional
import numpy as np
import pandas as pd

from app.evaluation.outcomes import point_size
from app.exit.exit_rules import check_stop_loss_exit, check_target_exit


def _simulate_single_path(
    direction: int,
    entry_pos: int,
    signal_atr: float,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    times: np.ndarray,
    z_arr: np.ndarray,
    max_bars: int = 6,
    stop_loss_atr: float = 1.5,
    step: np.timedelta64 = np.timedelta64(4, "h"),
) -> Optional[tuple[int, float, str, int, bool]]:
    """
    Simulates one trade path from entry_pos.
    Returns: (exit_pos, exit_price, exit_reason, bars_held, both_triggered) or None if unfinished.
    """
    n = len(opens)
    entry_price = float(opens[entry_pos])

    for bar_offset in range(max_bars + 1):
        curr = entry_pos + bar_offset
        if curr >= n:
            return None  # Data ended before exit

        bars_held = bar_offset

        # (a) Gap check
        if times[curr] - times[entry_pos] != bars_held * step:
            return (curr, float(opens[curr]), "gap_exit", bars_held, False)

        # (b) Stop FIRST check
        stop_decision = check_stop_loss_exit(
            direction=direction,
            entry_price=entry_price,
            current_high=float(highs[curr]),
            current_low=float(lows[curr]),
            current_atr=signal_atr,
            stop_loss_atr=stop_loss_atr,
        )
        if stop_decision is not None and stop_decision.should_exit:
            # If open was already past the stop, fill at the open
            if direction == 1:
                exit_price = min(float(stop_decision.exit_price), float(opens[curr]))
            else:
                exit_price = max(float(stop_decision.exit_price), float(opens[curr]))

            # Check if target condition was ALSO true on this exit candle
            target_decision = check_target_exit(
                direction=direction,
                current_close=float(closes[curr]),
                current_z_score=float(z_arr[curr]),
            )
            both = bool(target_decision is not None and target_decision.should_exit)
            return (curr, exit_price, "stop_loss", bars_held, both)

        # (c) Target check
        target_decision = check_target_exit(
            direction=direction,
            current_close=float(closes[curr]),
            current_z_score=float(z_arr[curr]),
        )
        if target_decision is not None and target_decision.should_exit:
            return (curr, float(closes[curr]), "target_equilibrium", bars_held, False)

        # (d) Time limit check
        if bars_held >= max_bars:
            return (curr, float(closes[curr]), "time_limit", bars_held, False)

    return None


def simulate_pair(
    symbol: str,
    candles_h4: pd.DataFrame,
    signals: pd.Series,
    atr_vals: pd.Series,
    z_scores: pd.Series,
    stop_loss_atr: float = 1.5,
    max_bars: int = 6,
) -> pd.DataFrame:
    """
    Simulates trades for one symbol following RULES_v2.md sections 4 and 5.
    """
    sig_arr = signals.to_numpy()
    atr_arr = atr_vals.to_numpy(dtype=float)
    z_arr = z_scores.to_numpy(dtype=float)
    opens = candles_h4["open"].to_numpy(dtype=float)
    highs = candles_h4["high"].to_numpy(dtype=float)
    lows = candles_h4["low"].to_numpy(dtype=float)
    closes = candles_h4["close"].to_numpy(dtype=float)
    times = candles_h4["time"].to_numpy()

    spread_first = candles_h4["spread_first"].to_numpy(dtype=float)
    if "spread" in candles_h4.columns:
        spread_col = candles_h4["spread"].to_numpy(dtype=float)
    elif "spread_worst" in candles_h4.columns:
        spread_col = candles_h4["spread_worst"].to_numpy(dtype=float)
    else:
        spread_col = spread_first

    point = point_size(symbol)
    step = np.timedelta64(4, "h")
    n = len(candles_h4)
    rows = []
    busy_until = 0

    for i in np.flatnonzero(sig_arr != 0):
        entry = i + 1
        if entry >= n:
            continue
        if entry < busy_until:
            continue
        if not (atr_arr[i] > 0):
            continue

        direction = int(sig_arr[i])
        signal_atr = float(atr_arr[i])

        # 1. Simulate real trade
        res_real = _simulate_single_path(
            direction=direction,
            entry_pos=entry,
            signal_atr=signal_atr,
            opens=opens,
            highs=highs,
            lows=lows,
            closes=closes,
            times=times,
            z_arr=z_arr,
            max_bars=max_bars,
            stop_loss_atr=stop_loss_atr,
            step=step,
        )
        if res_real is None:
            continue

        exit_pos, exit_price, exit_reason, bars_held, both_triggered = res_real

        # 2. Simulate opposite trade on same entry candle (mirrored exit path)
        res_opp = _simulate_single_path(
            direction=-direction,
            entry_pos=entry,
            signal_atr=signal_atr,
            opens=opens,
            highs=highs,
            lows=lows,
            closes=closes,
            times=times,
            z_arr=z_arr,
            max_bars=max_bars,
            stop_loss_atr=stop_loss_atr,
            step=step,
        )
        if res_opp is None:
            continue

        _, exit_price_opp, _, _, _ = res_opp

        entry_price = float(opens[entry])
        move_atr = float((exit_price - entry_price) / signal_atr)
        outcome_atr = float(direction * move_atr)

        move_atr_opp = float((exit_price_opp - entry_price) / signal_atr)
        outcome_atr_opposite = float((-direction) * move_atr_opp)

        cost_first_atr = float(spread_first[entry] * point / signal_atr)
        cost_worst_atr = float(spread_col[entry] * point / signal_atr)

        t_dt = pd.Timestamp(times[entry])
        week = str(t_dt.to_period("W"))
        quarter = f"{t_dt.year}Q{t_dt.quarter}"

        rows.append(
            {
                "symbol": symbol,
                "signal_pos": int(i),
                "entry_pos": int(entry),
                "entry_time": t_dt,
                "direction": int(direction),
                "exit_reason": str(exit_reason),
                "bars_held": int(bars_held),
                "move_atr": float(move_atr),
                "outcome_atr": float(outcome_atr),
                "outcome_atr_opposite": float(outcome_atr_opposite),
                "cost_first_atr": float(cost_first_atr),
                "cost_worst_atr": float(cost_worst_atr),
                "both_triggered_on_exit": bool(both_triggered),
                "week": week,
                "quarter": quarter,
            }
        )

        busy_until = exit_pos + 1

    return pd.DataFrame(rows)
