from fastapi import APIRouter, Query
from app.core.settings import PRODUCTION_WATCHLIST
from app.execution.mt5_executor import MT5Executor

router = APIRouter()

WATCHLIST = PRODUCTION_WATCHLIST


@router.get("/markets")
def get_markets():
    """Returns the market watchlist with real quotes from MT5 if available."""
    markets = []
    executor = None
    connected = False

    try:
        executor = MT5Executor()
        connected = executor.connect()
    except Exception:
        connected = False

    for symbol in WATCHLIST:
        bid = 0.0
        ask = 0.0
        spread_pips = 0.0

        if connected and executor and executor.mt5:
            try:
                tick = executor.mt5.symbol_info_tick(symbol)
                if tick:
                    bid = float(tick.bid)
                    ask = float(tick.ask)
                    point = executor.mt5.symbol_info(symbol).point or 0.0001
                    spread_pips = round((ask - bid) / (point * 10), 1)
            except Exception:
                pass

        markets.append({
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "spreadPips": spread_pips,
            "change24h": 0.0,
            "status": "LIVE" if (bid > 0) else "OFFLINE",
        })

    if executor:
        try:
            executor.close()
        except Exception:
            pass

    return markets


@router.get("/markets/{symbol}/candles")
def get_candles(
    symbol: str,
    timeframe: str = Query("5m", pattern="^(?i)(1m|5m|15m|30m|1h|4h|1d|1w|1mn|m1|m5|m15|m30|h1|h4|d1|w1|mn|mn1)$"),
    count: int = Query(100, ge=10, le=1000),
):
    """Fetches real candle OHLCV series for a symbol from MT5."""
    candles = []
    norm_tf = {
        "m1": "1m", "m5": "5m", "m15": "15m", "m30": "30m",
        "h1": "1h", "h4": "4h", "d1": "1d", "w1": "1w",
        "mn": "1mn", "mn1": "1mn",
    }.get(timeframe.lower(), timeframe.lower())
    try:
        executor = MT5Executor()
        if executor.connect():
            raw_candles = executor.fetch_candles(symbol, norm_tf, count)
            for c in raw_candles:
                candles.append({
                    "timestamp": c.timestamp.isoformat(),
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume or 0,
                })
            executor.close()
    except Exception:
        pass

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "count": len(candles),
        "candles": candles,
    }
