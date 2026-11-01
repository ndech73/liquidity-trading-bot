import pandas as pd
import pytest

from app.market_analyzer.volatility import (
    atr,
    bollinger_bands,
    bollinger_width,
    true_range,
)


def make_candles() -> pd.DataFrame:
    """Four small EURUSD candles with numbers we can check by hand."""
    return pd.DataFrame(
        {
            "high":  [1.1010, 1.1020, 1.1030, 1.1060],
            "low":   [1.1000, 1.1002, 1.1010, 1.1020],
            "close": [1.1005, 1.1015, 1.1025, 1.1050],
        }
    )


def test_true_range_matches_hand_calculation():
    # Candle 1: no previous close, so only high - low = 0.0010
    # Candle 2: biggest of 0.0018, 0.0015, 0.0003 = 0.0018
    # Candle 3: biggest of 0.0020, 0.0015, 0.0005 = 0.0020
    # Candle 4: biggest of 0.0040, 0.0035, 0.0005 = 0.0040
    result = true_range(make_candles())
    expected = [0.0010, 0.0018, 0.0020, 0.0040]
    assert list(result) == pytest.approx(expected)


def test_atr_matches_hand_calculation():
    # With period 2, the new candle gets 1/2 of the weight.
    # ATR 1 = (0.0010 + 0.0018) / 2           = 0.0014
    # ATR 2 = 0.5 * 0.0014  + 0.5 * 0.0020    = 0.0017
    # ATR 3 = 0.5 * 0.0017  + 0.5 * 0.0040    = 0.00285
    result = atr(make_candles(), period=2)
    assert pd.isna(result.iloc[0])  # not enough candles yet
    assert list(result.iloc[1:]) == pytest.approx([0.0014, 0.0017, 0.00285])


# Four closing prices we can check by hand, using windows of 2 closes.
CLOSES = pd.Series([10.0, 12.0, 16.0, 16.0])


def test_bollinger_bands_match_hand_calculation():
    # Window [10, 12]: mean 11, each close is 1 away, so std = 1
    #   upper = 11 + 2*1 = 13, lower = 11 - 2*1 = 9
    # Window [12, 16]: mean 14, each close is 2 away, so std = 2
    #   upper = 14 + 2*2 = 18, lower = 14 - 2*2 = 10
    # Window [16, 16]: mean 16, no spread, so std = 0
    #   upper = 16, lower = 16
    bands = bollinger_bands(CLOSES, period=2, num_std=2.0)

    assert pd.isna(bands["middle"].iloc[0])  # not enough closes yet
    assert list(bands["middle"].iloc[1:]) == pytest.approx([11.0, 14.0, 16.0])
    assert list(bands["upper"].iloc[1:]) == pytest.approx([13.0, 18.0, 16.0])
    assert list(bands["lower"].iloc[1:]) == pytest.approx([9.0, 10.0, 16.0])


def test_bollinger_width_matches_hand_calculation():
    # Width = (upper - lower) / middle
    # Window [10, 12]: (13 - 9)  / 11 = 4 / 11
    # Window [12, 16]: (18 - 10) / 14 = 8 / 14
    # Window [16, 16]: (16 - 16) / 16 = 0   (a perfect squeeze)
    width = bollinger_width(CLOSES, period=2, num_std=2.0)

    assert pd.isna(width.iloc[0])
    assert list(width.iloc[1:]) == pytest.approx([4 / 11, 8 / 14, 0.0])