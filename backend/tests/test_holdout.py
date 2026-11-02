import pandas as pd
import pytest

from app.data.downloader import save_candles
from app.data.loader import load_candles

# Two candles before the hold-out, two inside it, and one AFTER it ends.
TIMES = [
    "2025-09-13 22:00",
    "2025-09-13 23:00",
    "2025-09-14 00:00",
    "2025-09-14 01:00",
    "2026-09-14 00:00",
]


def make_file(folder):
    candles = pd.DataFrame(
        {
            "time": pd.to_datetime(TIMES),
            "open": 1.10,
            "high": 1.12,
            "low": 1.09,
            "close": 1.11,
            "volume": 100.0,
            "spread": 12.0,
        }
    )
    save_candles(candles, "EURUSD", "M15", folder=folder)


def test_default_gives_only_development_data(tmp_path):
    make_file(tmp_path)
    loaded = load_candles("EURUSD", "M15", folder=tmp_path)

    assert list(loaded["time"]) == list(pd.to_datetime(TIMES[:2]))


def test_holdout_is_refused_without_confirmation(tmp_path):
    make_file(tmp_path)
    with pytest.raises(PermissionError):
        load_candles("EURUSD", "M15", folder=tmp_path, part="holdout")


def test_holdout_with_confirmation_gives_only_the_holdout_year(tmp_path):
    make_file(tmp_path)
    loaded = load_candles(
        "EURUSD", "M15", folder=tmp_path, part="holdout", confirm_final_test=True
    )

    # The first holdout candle is included; the one on 2026-09-14 is not.
    assert list(loaded["time"]) == list(pd.to_datetime(TIMES[2:4]))


def test_holdout_use_is_written_to_the_log(tmp_path):
    make_file(tmp_path)
    log_path = tmp_path / "holdout_access.log"
    assert not log_path.exists()

    load_candles(
        "EURUSD", "M15", folder=tmp_path, part="holdout", confirm_final_test=True
    )

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    assert "EURUSD" in lines[0] and "M15" in lines[0]


def test_refused_holdout_is_not_logged(tmp_path):
    make_file(tmp_path)
    with pytest.raises(PermissionError):
        load_candles("EURUSD", "M15", folder=tmp_path, part="holdout")
    assert not (tmp_path / "holdout_access.log").exists()


def test_development_data_starts_again_at_row_zero(tmp_path):
    make_file(tmp_path)
    loaded = load_candles(
        "EURUSD", "M15", folder=tmp_path, part="holdout", confirm_final_test=True
    )
    assert list(loaded.index) == [0, 1]


def test_unknown_part_is_rejected(tmp_path):
    make_file(tmp_path)
    with pytest.raises(ValueError):
        load_candles("EURUSD", "M15", folder=tmp_path, part="everything")