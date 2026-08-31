from datetime import datetime, timezone

import pytest

from app.analysis_engine.domain.candle import Candle


def make_candle(**overrides) -> Candle:
    data = {
        "symbol": "EURUSD",
        "timeframe": "15m",
        "timestamp": datetime.now(timezone.utc),
        "open": 1.1000,
        "high": 1.1050,
        "low": 1.0950,
        "close": 1.1030,
    }
    data.update(overrides)
    return Candle(**data)


def test_candle_calculates_range():
    candle = make_candle()
    assert candle.range == pytest.approx(0.0100)


def test_candle_calculates_body():
    candle = make_candle()
    assert candle.body == pytest.approx(0.0030)


def test_candle_calculates_wicks():
    candle = make_candle()
    assert candle.upper_wick == pytest.approx(0.0020)
    assert candle.lower_wick == pytest.approx(0.0050)


def test_bullish_candle():
    candle = make_candle(open=1.1000, close=1.1030)
    assert candle.bullish is True
    assert candle.bearish is False
    assert candle.is_doji() is False


def test_bearish_candle():
    candle = make_candle(open=1.1030, close=1.1000)
    assert candle.bullish is False
    assert candle.bearish is True
    assert candle.is_doji() is False


def test_doji_candle():
    candle = make_candle(open=1.1000, close=1.1000)
    assert candle.is_doji() is True
    assert candle.bullish is False
    assert candle.bearish is False


def test_invalid_high_low_is_rejected():
    with pytest.raises(ValueError, match="high cannot be lower than low"):
        make_candle(high=1.0900, low=1.0950)


def test_invalid_open_is_rejected():
    with pytest.raises(ValueError, match="open must be between low and high"):
        make_candle(open=1.1100)


def test_invalid_close_is_rejected():
    with pytest.raises(ValueError, match="close must be between low and high"):
        make_candle(close=1.1100)


def test_negative_volume_is_rejected():
    with pytest.raises(ValueError, match="volume cannot be negative"):
        make_candle(volume=-1)


def test_candle_is_immutable():
    candle = make_candle()
    with pytest.raises(AttributeError):
        candle.close = 1.2000