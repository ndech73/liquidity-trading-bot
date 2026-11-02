import numpy as np
import pandas as pd
import pytest

from app.evaluation.outcomes import TRADE_COLUMNS, build_trades, point_size

ATR = 0.001  # a constant ATR keeps the hand calculations simple


def make_candles(n=40, spread=10.0, times=None):
    """
    Candles that rise by exactly 0.0001 per candle:
      open[i]  = 1.1 + 0.0001 * i
      close[i] = open[i] + 0.0001
    """
    if times is None:
        times = pd.date_range("2024-03-04 00:00", periods=n, freq="15min")
    opens = 1.1 + 0.0001 * np.arange(len(times))
    closes = opens + 0.0001
    return pd.DataFrame(
        {
            "time": times,
            "open": opens,
            "high": closes + 0.00005,
            "low": opens - 0.00005,
            "close": closes,
            "volume": 100.0,
            "spread": spread,
        }
    )


def signals_at(n, **positions):
    """signals_at(40, p3=1, p11=-1) puts +1 at candle 3 and -1 at candle 11."""
    values = np.zeros(n, dtype=int)
    for name, direction in positions.items():
        values[int(name[1:])] = direction
    return pd.Series(values)


def atr_series(n, value=ATR):
    return pd.Series([value] * n)


def test_long_trade_matches_hand_calculation():
    candles = make_candles()
    trades = build_trades("EURUSD", candles, signals_at(40, p3=1), atr_series(40))

    assert len(trades) == 1
    trade = trades.iloc[0]
    # Entry = open of candle 4 = 1.1004. Exit = close of candle 11 = 1.1012.
    # Change = 0.0008, and 0.0008 / 0.001 = 0.8 ATR.
    assert trade["move_atr"] == pytest.approx(0.8)
    assert trade["outcome_atr"] == pytest.approx(0.8)
    assert trade["direction"] == 1
    assert trade["entry_time"] == candles["time"].iloc[4]
    # Spread 10 points * 0.00001 = 0.0001, and 0.0001 / 0.001 = 0.1 ATR.
    assert trade["cost_atr"] == pytest.approx(0.1)


def test_short_trade_flips_the_sign_but_not_the_move():
    trades = build_trades("EURUSD", make_candles(), signals_at(40, p3=-1), atr_series(40))
    trade = trades.iloc[0]
    assert trade["move_atr"] == pytest.approx(0.8)
    assert trade["outcome_atr"] == pytest.approx(-0.8)


def test_changing_the_signal_candles_close_changes_nothing():
    """Entry is the NEXT candle's open, so the signal candle's own close is not used."""
    candles = make_candles()
    first = build_trades("EURUSD", candles, signals_at(40, p3=1), atr_series(40))

    changed = candles.copy()
    changed.loc[3, "close"] = 9.99
    second = build_trades("EURUSD", changed, signals_at(40, p3=1), atr_series(40))

    assert first["outcome_atr"].iloc[0] == pytest.approx(second["outcome_atr"].iloc[0])


def test_signal_while_a_trade_is_open_is_skipped():
    # Trade 1: signal at 3, uses candles 4..11. Signal at 5 enters at 6 -> skipped.
    # Signal at 10 enters at 11 -> still inside trade 1 -> skipped.
    # Signal at 11 enters at 12 -> free -> allowed.
    signals = signals_at(40, p3=1, p5=1, p10=-1, p11=-1)
    trades = build_trades("EURUSD", make_candles(), signals, atr_series(40))
    assert list(trades["signal_pos"]) == [3, 11]


def test_signal_too_close_to_the_end_is_dropped():
    signals = signals_at(40, p3=1, p35=1)  # 35 + 8 = 43, past the last candle
    trades = build_trades("EURUSD", make_candles(), signals, atr_series(40))
    assert list(trades["signal_pos"]) == [3]


def test_trade_that_crosses_a_gap_is_skipped():
    first = pd.date_range("2024-03-01 00:00", periods=20, freq="15min")
    second = pd.date_range("2024-03-04 00:00", periods=20, freq="15min")  # after a weekend
    candles = make_candles(times=first.append(second))

    # 15: runs into the gap. 19: signal is last before the gap, entry is after it.
    # 25: all candles are after the gap -> allowed.
    signals = signals_at(40, p15=1, p19=1, p25=1)
    trades = build_trades("EURUSD", candles, signals, atr_series(40))
    assert list(trades["signal_pos"]) == [25]


def test_signal_without_an_atr_yet_is_skipped():
    atr = atr_series(40)
    atr.iloc[3] = np.nan
    trades = build_trades("EURUSD", make_candles(), signals_at(40, p3=1, p20=1), atr)
    assert list(trades["signal_pos"]) == [20]


def test_jpy_pairs_use_a_bigger_point():
    assert point_size("EURUSD") == pytest.approx(0.00001)
    assert point_size("EURJPY") == pytest.approx(0.001)

    # spread 10 points on a JPY pair = 0.01 price; ATR 0.1 -> cost 0.1
    trades = build_trades("EURJPY", make_candles(), signals_at(40, p3=1), atr_series(40, 0.1))
    assert trades["cost_atr"].iloc[0] == pytest.approx(0.1)


def test_bad_signal_values_are_rejected():
    with pytest.raises(ValueError):
        build_trades("EURUSD", make_candles(), signals_at(40, p3=2), atr_series(40))


def test_wrong_length_is_rejected():
    with pytest.raises(ValueError):
        build_trades("EURUSD", make_candles(), signals_at(39, p3=1), atr_series(40))


def test_no_signals_gives_an_empty_table_with_the_right_columns():
    trades = build_trades("EURUSD", make_candles(), signals_at(40), atr_series(40))
    assert len(trades) == 0
    assert list(trades.columns) == TRADE_COLUMNS


def test_week_and_quarter_labels_follow_the_entry_time():
    trades = build_trades("EURUSD", make_candles(), signals_at(40, p3=1), atr_series(40))
    # 2024-03-04 is a Monday in Q1 2024.
    assert trades["quarter"].iloc[0] == "2024Q1"
    assert trades["week"].iloc[0].startswith("2024-03-04")
