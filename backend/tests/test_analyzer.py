import numpy as np
import pandas as pd
import pytest

from app.market_analyzer.analyzer import MarketAnalyzer
from app.market_analyzer.volume_profile import value_area, volume_profile, vpoc

BIN_SIZE = 0.0001
SETTINGS = dict(
    bin_size=BIN_SIZE,
    zscore_window=50,
    profile_window=100,
)


def make_candles(n=300, seed=0):
    """Fake but realistic-looking candles (a random walk around 1.10)."""
    rng = np.random.default_rng(seed)
    close = 1.1 + np.cumsum(rng.normal(0, 0.0005, n))
    open_ = np.concatenate([[1.1], close[:-1]])
    high = np.maximum(open_, close) + rng.uniform(0, 0.0003, n)
    low = np.minimum(open_, close) - rng.uniform(0, 0.0003, n)
    volume = rng.integers(50, 500, n)
    return pd.DataFrame(
        {"high": high, "low": low, "close": close, "volume": volume}
    )


def level_ids(levels):
    """A simple, comparable list of (candle, kind) for each level."""
    return sorted(zip(levels["position"], levels["kind"]))


@pytest.mark.parametrize("at", [150, 200, 299])
def test_no_look_ahead(at):
    """
    THE most important test.
    Answers using ALL the candles must equal answers using ONLY candles
    up to `at`. If they differ, the analyzer is peeking into the future.
    """
    candles = make_candles()
    full = MarketAnalyzer(candles, **SETTINGS).state_at(at)

    cut_candles = candles.iloc[: at + 1].reset_index(drop=True)
    cut = MarketAnalyzer(cut_candles, **SETTINGS).state_at(at)

    assert full.atr == pytest.approx(cut.atr)
    assert full.bb_width == pytest.approx(cut.bb_width)
    assert full.width_zscore == pytest.approx(cut.width_zscore)
    assert full.vpoc == pytest.approx(cut.vpoc)
    assert full.value_area_low == pytest.approx(cut.value_area_low)
    assert full.value_area_high == pytest.approx(cut.value_area_high)
    assert level_ids(full.active_levels) == level_ids(cut.active_levels)

    # The WHOLE levels table must match too, every column. A column that
    # only exists in the full-data version can hide future information.
    assert list(full.active_levels.columns) == list(cut.active_levels.columns)
    assert full.active_levels.reset_index(drop=True).equals(
        cut.active_levels.reset_index(drop=True)
    )


def test_active_levels_do_not_reveal_the_future():
    """
    A level that is still active has not been crossed yet. Its "swept_at"
    could only hold a FUTURE candle number, so it must not be handed out.
    """
    state = MarketAnalyzer(make_candles(), **SETTINGS).state_at(150)

    assert "swept_at" not in state.active_levels.columns
    assert (state.active_levels["known_at"] <= 150).all()


def test_volume_profile_uses_only_the_recent_window():
    candles = make_candles(n=20)
    analyzer = MarketAnalyzer(
        candles, bin_size=BIN_SIZE, profile_window=5, zscore_window=5
    )
    state = analyzer.state_at(19)

    last_five = candles.iloc[15:20]
    profile = volume_profile(last_five, BIN_SIZE)
    expected_low, expected_high = value_area(profile)

    assert state.vpoc == pytest.approx(vpoc(profile))
    assert state.value_area_low == pytest.approx(expected_low)
    assert state.value_area_high == pytest.approx(expected_high)


def test_early_candles_have_no_volatility_answers_yet():
    state = MarketAnalyzer(make_candles(), **SETTINGS).state_at(10)

    assert state.atr is None
    assert state.bb_width is None
    assert state.width_zscore is None


@pytest.mark.parametrize("bad_position", [-1, 300])
def test_position_outside_the_data_is_rejected(bad_position):
    analyzer = MarketAnalyzer(make_candles(n=300), **SETTINGS)
    with pytest.raises(ValueError):
        analyzer.state_at(bad_position)


def test_sudden_jump_gives_a_big_positive_zscore():
    """A calm market followed by one big jump should look 'unusually wild'."""
    rng = np.random.default_rng(1)
    close = 1.1 + rng.normal(0, 0.0001, 160)  # calm
    close[150] = 1.11                          # one big jump
    candles = pd.DataFrame(
        {
            "high": close + 0.0002,
            "low": close - 0.0002,
            "close": close,
            "volume": 100,
        }
    )

    state = MarketAnalyzer(
        candles, bin_size=BIN_SIZE, zscore_window=100, profile_window=100
    ).state_at(150)

    assert state.width_zscore is not None
    assert state.width_zscore > 3