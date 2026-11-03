import pandas as pd


# ---------------------------------------------------------------
# 1. ATR (Average True Range) - Measuring Candle Size
# ---------------------------------------------------------------

def true_range(candles: pd.DataFrame) -> pd.Series:
    previous_close = candles["close"].shift(1)

    candle_size = candles["high"] - candles["low"]
    up_from_previous_close = (candles["high"] - previous_close).abs()
    down_from_previous_close = (candles["low"] - previous_close).abs()

    all_three = pd.concat(
        [candle_size, up_from_previous_close, down_from_previous_close],
        axis=1,
    )
    return all_three.max(axis=1)


def atr(candles: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = true_range(candles)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


# ---------------------------------------------------------------
# 2. Bollinger Bands & Band Width - Measuring Corridor Size
# ---------------------------------------------------------------

def bollinger_bands(
    close: pd.Series, period: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    window = close.rolling(window=period)
    middle = window.mean()
    std = window.std(ddof=0)

    return pd.DataFrame(
        {
            "middle": middle,
            "upper": middle + num_std * std,
            "lower": middle - num_std * std,
        }
    )


def bollinger_width(
    close: pd.Series, period: int = 20, num_std: float = 2.0
) -> pd.Series:
    bands = bollinger_bands(close, period, num_std)
    return (bands["upper"] - bands["lower"]) / bands["middle"]