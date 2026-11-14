import inspect
from datetime import datetime
import pytest
from app.data.downloader import CHUNK_DAYS, download_candles, main


def test_download_candles_has_chunk_days_parameter():
    sig = inspect.signature(download_candles)
    assert "chunk_days" in sig.parameters
    assert sig.parameters["chunk_days"].default == CHUNK_DAYS
    assert sig.parameters["chunk_days"].default == 90


def test_downloader_parser_chunk_days(monkeypatch):
    import argparse
    # Test default
    test_args = ["downloader.py", "EURUSD", "--start", "2024-01-01", "--end", "2024-01-02"]
    monkeypatch.setattr("sys.argv", test_args)

    called_kwargs = {}

    def mock_download(symbol, timeframe, start, end, chunk_days=90):
        called_kwargs["chunk_days"] = chunk_days
        import pandas as pd
        return pd.DataFrame({"time": [], "open": [], "high": [], "low": [], "close": [], "volume": [], "spread": []})

    def mock_save(candles, symbol, timeframe):
        return "fake_path"

    monkeypatch.setattr("app.data.downloader.download_candles", mock_download)
    monkeypatch.setattr("app.data.downloader.save_candles", mock_save)

    main()
    assert called_kwargs["chunk_days"] == 90

    # Test explicit --chunk-days 365
    test_args_explicit = ["downloader.py", "EURUSD", "--start", "2024-01-01", "--end", "2024-01-02", "--chunk-days", "365"]
    monkeypatch.setattr("sys.argv", test_args_explicit)
    main()
    assert called_kwargs["chunk_days"] == 365
