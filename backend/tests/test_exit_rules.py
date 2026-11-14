"""
test_exit_rules.py
------------------
Unit tests for mathematical exit decision logic.
"""

import pandas as pd
import pytest

from app.exit.exit_rules import ExitDecision, check_trade_exit


def make_candle(open_p=1.1000, high=1.1020, low=1.0980, close=1.1010):
    return pd.Series({"open": open_p, "high": high, "low": low, "close": close})


def test_target_equilibrium_exit_long():
    # Long trade entered at 1.0950 when z was -2.5
    # Current candle reaches z = 0.1 (returned to average)
    candle = make_candle(close=1.1000)
    decision = check_trade_exit(
        direction=1,
        entry_price=1.0950,
        current_candle=candle,
        current_z_score=0.1,
        current_atr=0.0010,
        bars_held=4,
        max_bars=16,
    )

    assert decision is not None
    assert decision.should_exit is True
    assert decision.exit_reason == "target_equilibrium"
    assert decision.exit_price == 1.1000


def test_stop_loss_exit_long():
    # Long trade entered at 1.1000 with 1.5 ATR stop loss (ATR = 0.0010 -> stop at 1.0985)
    # Candle low pierces down to 1.0980
    candle = make_candle(high=1.0995, low=1.0980, close=1.0982)
    decision = check_trade_exit(
        direction=1,
        entry_price=1.1000,
        current_candle=candle,
        current_z_score=-2.8,
        current_atr=0.0010,
        bars_held=2,
        max_bars=16,
        stop_loss_atr=1.5,
    )

    assert decision is not None
    assert decision.should_exit is True
    assert decision.exit_reason == "stop_loss"
    assert decision.exit_price == pytest.approx(1.0985)


def test_time_limit_exit():
    # Price neither hits target nor stop, but reaches max 16 bars
    candle = make_candle(high=1.1005, low=1.0995, close=1.1001)
    decision = check_trade_exit(
        direction=1,
        entry_price=1.1000,
        current_candle=candle,
        current_z_score=-0.5,
        current_atr=0.0010,
        bars_held=16,
        max_bars=16,
    )

    assert decision is not None
    assert decision.should_exit is True
    assert decision.exit_reason == "time_limit"


def test_full_swing_target_exit():
    # Long trade with target_z = 0.8
    candle = make_candle(close=1.1050)
    # If z is only 0.2, target_z=0.8 does NOT trigger exit
    d_holding = check_trade_exit(
        direction=1,
        entry_price=1.0950,
        current_candle=candle,
        current_z_score=0.2,
        current_atr=0.0010,
        bars_held=4,
        max_bars=16,
        target_z=0.8,
    )
    assert d_holding is None

    # When z reaches 0.85, full swing target triggers!
    d_exit = check_trade_exit(
        direction=1,
        entry_price=1.0950,
        current_candle=candle,
        current_z_score=0.85,
        current_atr=0.0010,
        bars_held=6,
        max_bars=16,
        target_z=0.8,
    )
    assert d_exit is not None
    assert d_exit.should_exit is True
    assert d_exit.exit_reason == "target_full_swing"
    assert d_exit.exit_price == 1.1050


def test_stop_loss_precedence_over_target():
    # Candle that hits both stop (low <= 1.0985) and target (z >= 0.0)
    candle = make_candle(high=1.1020, low=1.0980, close=1.1010)
    decision = check_trade_exit(
        direction=1,
        entry_price=1.1000,
        current_candle=candle,
        current_z_score=0.5,
        current_atr=0.0010,
        bars_held=2,
        max_bars=16,
        stop_loss_atr=1.5,
    )
    # Stop loss must take precedence!
    assert decision is not None
    assert decision.exit_reason == "stop_loss"
