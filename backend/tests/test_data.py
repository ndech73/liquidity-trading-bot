import pandas as pd
import pytest

from app.data.downloader import CANDLE_COLUMNS, rates_to_candles, save_candles
from app.data.loader import find_gaps, load_candles, validate_candles


def raw_rates(times):
    """A tiny fake table shaped like MT5's raw answer."""
    n = len(times)
    return pd.DataFrame(
        {
            "time": times,
            "open": [1.10] * n,
            "high": [1.12] * n,
            "low": [1.09] * n,
            "close": [1.11] * n,
            "tick_volume": [100] * n,
            "spread": [12] * n,
            "real_volume": [0] * n,
        }
    )


def clean_candles(n=4):
    times = pd.date_range("2024-01-05 00:00", periods=n, freq="15min")
    return pd.DataFrame(
        {
            "time": times,
            "open": 1.10,
            "high": 1.12,
            "low": 1.09,
            "close": 1.11,
            "volume": 100.0,
            "spread": 12.0,
        }
    )


# ---------- converting raw MT5 numbers ----------

def test_conversion_gives_standard_columns_and_real_dates():
    candles = rates_to_candles(raw_rates([0, 900]))  # 0 and 900 seconds
    assert list(candles.columns) == CANDLE_COLUMNS
    assert candles["time"].iloc[0] == pd.Timestamp("1970-01-01 00:00:00")
    assert candles["time"].iloc[1] == pd.Timestamp("1970-01-01 00:15:00")


def test_conversion_sorts_and_removes_repeated_times():
    candles = rates_to_candles(raw_rates([1800, 0, 900, 900]))
    assert candles["time"].is_monotonic_increasing
    assert len(candles) == 3


def test_tick_volume_becomes_volume():
    candles = rates_to_candles(raw_rates([0]))
    assert candles["volume"].iloc[0] == 100


# ---------- saving and loading ----------

def test_save_then_load_gives_the_same_candles(tmp_path):
    original = clean_candles()
    save_candles(original, "EURUSD", "M15", folder=tmp_path)
    loaded = load_candles("EURUSD", "M15", folder=tmp_path)
    pd.testing.assert_frame_equal(original, loaded)


def test_loading_a_missing_file_gives_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_candles("EURUSD", "M15", folder=tmp_path)


# ---------- the cleanliness checks ----------

def test_clean_candles_pass_validation():
    validate_candles(clean_candles())  # should not raise


def test_missing_column_is_caught():
    with pytest.raises(ValueError, match="Missing columns"):
        validate_candles(clean_candles().drop(columns=["spread"]))


def test_empty_value_is_caught():
    candles = clean_candles()
    candles.loc[1, "close"] = None
    with pytest.raises(ValueError, match="empty"):
        validate_candles(candles)


def test_repeated_time_is_caught():
    candles = clean_candles()
    candles.loc[2, "time"] = candles.loc[1, "time"]
    with pytest.raises(ValueError, match="order"):
        validate_candles(candles)


def test_wrong_order_is_caught():
    candles = clean_candles().iloc[::-1].reset_index(drop=True)
    with pytest.raises(ValueError, match="order"):
        validate_candles(candles)


def test_high_below_low_is_caught():
    candles = clean_candles()
    candles.loc[0, "high"] = 1.00  # below the low of 1.09
    with pytest.raises(ValueError, match="high"):
        validate_candles(candles)


def test_close_above_high_is_caught():
    candles = clean_candles()
    candles.loc[0, "close"] = 1.50  # above the high of 1.12
    with pytest.raises(ValueError, match="high"):
        validate_candles(candles)


def test_negative_volume_is_caught():
    candles = clean_candles()
    candles.loc[0, "volume"] = -5
    with pytest.raises(ValueError, match="Volume"):
        validate_candles(candles)


# ---------- gaps ----------

def test_find_gaps_reports_only_the_big_jump():
    times = pd.to_datetime(
        ["2026-01-05 00:00", "2026-01-05 00:15", "2026-01-05 10:15", "2026-01-05 10:30"]
    )
    candles = clean_candles(4)
    candles["time"] = times

    gaps = find_gaps(candles, min_hours=6)

    assert len(gaps) == 1
    assert gaps["gap_start"].iloc[0] == pd.Timestamp("2026-01-05 00:15")
    assert gaps["gap_end"].iloc[0] == pd.Timestamp("2026-01-05 10:15")
    assert gaps["hours"].iloc[0] == pytest.approx(10.0)


def test_no_gaps_in_continuous_data():
    assert len(find_gaps(clean_candles(10))) == 0