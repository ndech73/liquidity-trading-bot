import pandas as pd
import pytest
from app.evaluation.resample import resample_m15


def test_spread_first_h1():
    # 4 M15 candles for 1 H1 bar
    times = pd.date_range("2024-01-01 00:00:00", periods=4, freq="15min")
    df = pd.DataFrame(
        {
            "time": times,
            "open": [1.1000, 1.1005, 1.1010, 1.1015],
            "high": [1.1010, 1.1020, 1.1015, 1.1025],
            "low": [1.0995, 1.1000, 1.1005, 1.1010],
            "close": [1.1005, 1.1010, 1.1015, 1.1020],
            "volume": [100, 150, 200, 250],
            "spread": [10.0, 25.0, 15.0, 8.0],
        }
    )

    res, dropped = resample_m15(df, "H1")
    assert dropped == 0
    assert len(res) == 1
    assert res.iloc[0]["spread_first"] == 10.0
    assert res.iloc[0]["spread_worst"] == 25.0
    assert res.iloc[0]["spread"] == 25.0


def test_spread_first_h4():
    # 16 M15 candles for 1 H4 bar
    times = pd.date_range("2024-01-01 00:00:00", periods=16, freq="15min")
    spreads = [12.0] + [20.0] * 14 + [50.0]
    df = pd.DataFrame(
        {
            "time": times,
            "open": [1.1000] * 16,
            "high": [1.1050] * 16,
            "low": [1.0950] * 16,
            "close": [1.1020] * 16,
            "volume": [100] * 16,
            "spread": spreads,
        }
    )

    res, dropped = resample_m15(df, "H4")
    assert dropped == 0
    assert len(res) == 1
    assert res.iloc[0]["spread_first"] == 12.0
    assert res.iloc[0]["spread_worst"] == 50.0
    assert res.iloc[0]["spread"] == 50.0
