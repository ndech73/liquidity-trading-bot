import numpy as np
import pandas as pd
import pytest

from app.evaluation.final_sim import simulate_pair


def make_h4_candles(opens, highs, lows, closes, spread_first=10.0, spread_worst=20.0, times=None):
    n = len(opens)
    if times is None:
        times = pd.date_range("2024-01-01 00:00:00", periods=n, freq="4h")
    return pd.DataFrame(
        {
            "time": times,
            "open": np.array(opens, dtype=float),
            "high": np.array(highs, dtype=float),
            "low": np.array(lows, dtype=float),
            "close": np.array(closes, dtype=float),
            "volume": np.ones(n, dtype=float) * 100,
            "spread_first": np.ones(n, dtype=float) * spread_first,
            "spread_worst": np.ones(n, dtype=float) * spread_worst,
            "spread": np.ones(n, dtype=float) * spread_worst,
        }
    )


# ----------------------------------------------------------------------
# (i) Stop touches AND closes at target -> exits by stop (Stop FIRST)
# ----------------------------------------------------------------------
def test_stop_first_long():
    # Long: signal at 0, entry at 1. Entry open = 100, ATR = 10, Stop = 100 - 15 = 85.
    # Candle 1 touches 84 (stop hit!) and closes at 105 with z = 0 (target hit!).
    candles = make_h4_candles(
        opens=[100, 100, 100],
        highs=[105, 105, 105],
        lows=[95, 84, 95],
        closes=[100, 105, 100],
    )
    signals = pd.Series([1, 0, 0])
    atr_vals = pd.Series([10.0, 10.0, 10.0])
    z_scores = pd.Series([-1.0, 0.0, 0.0])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["exit_reason"] == "stop_loss"
    assert t["exit_price"] == 85.0 if "exit_price" in t else True
    assert bool(t["both_triggered_on_exit"]) is True
    # Outcome for long stopped out at 85 from 100 is (85 - 100) / 10 = -1.5 ATR
    assert pytest.approx(t["outcome_atr"], 0.001) == -1.5


def test_stop_first_short():
    # Short: signal at 0, entry at 1. Entry open = 100, ATR = 10, Stop = 100 + 15 = 115.
    # Candle 1 touches 116 (stop hit!) and closes at 95 with z = 0 (target hit!).
    candles = make_h4_candles(
        opens=[100, 100, 100],
        highs=[105, 116, 105],
        lows=[95, 95, 95],
        closes=[100, 95, 100],
    )
    signals = pd.Series([-1, 0, 0])
    atr_vals = pd.Series([10.0, 10.0, 10.0])
    z_scores = pd.Series([1.0, 0.0, 0.0])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["exit_reason"] == "stop_loss"
    assert bool(t["both_triggered_on_exit"]) is True
    # Outcome for short stopped out at 115 from 100 is -1 * (115 - 100) / 10 = -1.5 ATR
    assert pytest.approx(t["outcome_atr"], 0.001) == -1.5


# ----------------------------------------------------------------------
# (ii) Candle opens past stop -> fills at open
# ----------------------------------------------------------------------
def test_open_past_stop_long():
    # Long: Entry at 1 (open = 100), ATR = 10, Stop = 85.
    # Candle 1 holds (low 90). Candle 2 opens at 80 (past stop 85).
    candles = make_h4_candles(
        opens=[100, 100, 80, 80],
        highs=[105, 102, 82, 82],
        lows=[95, 90, 78, 78],
        closes=[100, 92, 80, 80],
    )
    signals = pd.Series([1, 0, 0, 0])
    atr_vals = pd.Series([10.0, 10.0, 10.0, 10.0])
    z_scores = pd.Series([-2.0, -1.5, -2.0, -2.0])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["exit_reason"] == "stop_loss"
    # Outcome: (80 - 100) / 10 = -2.0 ATR
    assert pytest.approx(t["outcome_atr"], 0.001) == -2.0


def test_open_past_stop_short():
    # Short: Entry at 1 (open = 100), ATR = 10, Stop = 115.
    # Candle 1 holds (high 110). Candle 2 opens at 120 (past stop 115).
    candles = make_h4_candles(
        opens=[100, 100, 120, 120],
        highs=[105, 110, 125, 125],
        lows=[95, 98, 118, 118],
        closes=[100, 108, 122, 122],
    )
    signals = pd.Series([-1, 0, 0, 0])
    atr_vals = pd.Series([10.0, 10.0, 10.0, 10.0])
    z_scores = pd.Series([2.0, 1.5, 2.0, 2.0])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["exit_reason"] == "stop_loss"
    # Outcome: -1 * (120 - 100) / 10 = -2.0 ATR
    assert pytest.approx(t["outcome_atr"], 0.001) == -2.0


# ----------------------------------------------------------------------
# (iii) Normal target exit at close
# ----------------------------------------------------------------------
def test_normal_target_exit_long():
    # Long: Entry at 1 (open 100). Candle 1 z=-1.0. Candle 2 z=0.2 (target!), close=106.
    candles = make_h4_candles(
        opens=[100, 100, 104, 106],
        highs=[105, 104, 108, 108],
        lows=[95, 96, 102, 102],
        closes=[100, 102, 106, 106],
    )
    signals = pd.Series([1, 0, 0, 0])
    atr_vals = pd.Series([10.0, 10.0, 10.0, 10.0])
    z_scores = pd.Series([-2.0, -1.0, 0.2, 0.5])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["exit_reason"] == "target_equilibrium"
    assert t["bars_held"] == 1
    # Outcome: (106 - 100) / 10 = +0.6 ATR
    assert pytest.approx(t["outcome_atr"], 0.001) == 0.6


def test_normal_target_exit_short():
    # Short: Entry at 1 (open 100). Candle 1 z=1.0. Candle 2 z=-0.1 (target!), close=94.
    candles = make_h4_candles(
        opens=[100, 100, 96, 94],
        highs=[105, 102, 98, 98],
        lows=[95, 94, 92, 92],
        closes=[100, 98, 94, 94],
    )
    signals = pd.Series([-1, 0, 0, 0])
    atr_vals = pd.Series([10.0, 10.0, 10.0, 10.0])
    z_scores = pd.Series([2.0, 1.0, -0.1, -0.5])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["exit_reason"] == "target_equilibrium"
    assert t["bars_held"] == 1
    # Outcome: -1 * (94 - 100) / 10 = +0.6 ATR
    assert pytest.approx(t["outcome_atr"], 0.001) == 0.6


# ----------------------------------------------------------------------
# (iv) Time-limit exit after 6 candles
# ----------------------------------------------------------------------
def test_time_limit_exit():
    # 8 candles: signal at 0, entry at 1. No stop, z stays negative for long.
    # Exits on candle 1 + 6 = 7 at close.
    n = 9
    candles = make_h4_candles(
        opens=[100] * n,
        highs=[105] * n,
        lows=[95] * n,
        closes=[102] * n,
    )
    signals = pd.Series([1] + [0] * (n - 1))
    atr_vals = pd.Series([10.0] * n)
    z_scores = pd.Series([-1.0] * n)

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores, max_bars=6)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["exit_reason"] == "time_limit"
    assert t["bars_held"] == 6


# ----------------------------------------------------------------------
# (v) Missing candle gives gap_exit at next open
# ----------------------------------------------------------------------
def test_gap_exit():
    times = [
        pd.Timestamp("2024-01-01 00:00:00"),  # signal
        pd.Timestamp("2024-01-01 04:00:00"),  # entry
        pd.Timestamp("2024-01-01 12:00:00"),  # gap! jumped 8h instead of 4h
    ]
    candles = make_h4_candles(
        opens=[100, 100, 103],
        highs=[105, 105, 106],
        lows=[95, 95, 98],
        closes=[100, 102, 104],
        times=times,
    )
    signals = pd.Series([1, 0, 0])
    atr_vals = pd.Series([10.0, 10.0, 10.0])
    z_scores = pd.Series([-1.0, -1.0, -1.0])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert t["exit_reason"] == "gap_exit"
    # Fills at candle 2 open = 103: (103 - 100) / 10 = +0.3 ATR
    assert pytest.approx(t["outcome_atr"], 0.001) == 0.3


# ----------------------------------------------------------------------
# (vi) Overlapping signal is skipped
# ----------------------------------------------------------------------
def test_overlapping_signal_skipped():
    # Signal at 0 (entry 1). Exits at candle 2 on target.
    # Signal at 1 (entry 2) is during open trade -> must be skipped!
    candles = make_h4_candles(
        opens=[100, 100, 104, 105],
        highs=[105, 104, 108, 108],
        lows=[95, 96, 102, 102],
        closes=[100, 102, 106, 106],
    )
    signals = pd.Series([1, 1, 0, 0])
    atr_vals = pd.Series([10.0, 10.0, 10.0, 10.0])
    z_scores = pd.Series([-2.0, -1.0, 0.2, 0.5])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    assert trades.iloc[0]["signal_pos"] == 0


# ----------------------------------------------------------------------
# (vii) Cost uses spread_first, not worst spread
# ----------------------------------------------------------------------
def test_cost_uses_spread_first():
    candles = make_h4_candles(
        opens=[100, 100, 100],
        highs=[105, 105, 105],
        lows=[95, 95, 95],
        closes=[100, 100, 100],
        spread_first=8.0,
        spread_worst=35.0,
    )
    signals = pd.Series([1, 0, 0])
    # For EURUSD point_size = 0.00001. If ATR is 0.00080 (80 pips),
    # cost_first_atr = 8.0 * 0.00001 / 0.00080 = 0.1000
    # cost_worst_atr = 35.0 * 0.00001 / 0.00080 = 0.4375
    atr_vals = pd.Series([0.00080, 0.00080, 0.00080])
    z_scores = pd.Series([-1.0, 0.0, 0.0])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    t = trades.iloc[0]
    assert pytest.approx(t["cost_first_atr"], 0.0001) == 0.1000
    assert pytest.approx(t["cost_worst_atr"], 0.0001) == 0.4375
    assert t["cost_first_atr"] < t["cost_worst_atr"]


# ----------------------------------------------------------------------
# (viii) outcome_atr_opposite is computed with its own exit path
# ----------------------------------------------------------------------
def test_outcome_atr_opposite_independent_path():
    # Long trade: entry at 1 (open 100).
    # Candle 1: high=102, low=84 (Long hits stop 85!). Close=90, z=-1.
    # Meanwhile, for Short trade: entry 100. Stop is 115. Low is 84. Close=90 with z=-1 (Short hits target!).
    candles = make_h4_candles(
        opens=[100, 100, 100],
        highs=[105, 102, 105],
        lows=[95, 84, 95],
        closes=[100, 90, 100],
    )
    signals = pd.Series([1, 0, 0])
    atr_vals = pd.Series([10.0, 10.0, 10.0])
    z_scores = pd.Series([-2.0, -1.0, 0.0])

    trades = simulate_pair("EURUSD", candles, signals, atr_vals, z_scores)
    assert len(trades) == 1
    t = trades.iloc[0]
    # Real Long trade exited by stop: (85 - 100) / 10 = -1.5 ATR
    assert t["exit_reason"] == "stop_loss"
    assert pytest.approx(t["outcome_atr"], 0.001) == -1.5
    # Opposite Short trade exited by target at close (90): -1 * (90 - 100) / 10 = +1.0 ATR
    assert pytest.approx(t["outcome_atr_opposite"], 0.001) == 1.0
