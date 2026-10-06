from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

from app.strategy.trading_runner import trading_runner

router = APIRouter()


class ToggleModeRequest(BaseModel):
    auto_trade_enabled: bool


@router.get("/notifications/alerts")
def get_alerts():
    """Returns recent liquidity sweep & trade signal alerts."""
    return {
        "status": "ok",
        "alerts": trading_runner.recent_alerts,
        "total": len(trading_runner.recent_alerts),
    }


@router.get("/notifications/status")
def get_notification_status():
    """Returns scanner mode, watchlist, and active configuration."""
    return {
        "status": "ok",
        "mode": "ALERT_SCANNER" if not trading_runner.auto_trade_enabled else "AUTO_TRADE",
        "auto_trade_enabled": trading_runner.auto_trade_enabled,
        "watchlist": trading_runner.watchlist,
        "total_alerts": len(trading_runner.recent_alerts),
        "cooldown_minutes": trading_runner.symbol_cooldown_minutes,
    }


@router.post("/notifications/mode")
def set_trading_mode(req: ToggleModeRequest):
    """Enables or disables auto-trade execution vs alert scanner mode."""
    trading_runner.auto_trade_enabled = req.auto_trade_enabled
    mode_str = "AUTO_TRADE" if trading_runner.auto_trade_enabled else "ALERT_SCANNER"
    return {
        "status": "ok",
        "mode": mode_str,
        "auto_trade_enabled": trading_runner.auto_trade_enabled,
    }


@router.post("/notifications/test")
def trigger_test_alert():
    """Dispatches a mock test liquidity alert over WebSocket to verify sound & desktop notifications."""
    now_utc = datetime.now(timezone.utc)
    mock_alert = {
        "id": f"test-alert-{int(now_utc.timestamp())}",
        "symbol": "GBPUSD",
        "timeframe": "15m",
        "direction": "BUY",
        "entryPrice": 1.30542,
        "stopLoss": 1.30320,
        "takeProfit1": 1.30808,
        "takeProfit2": 1.31208,
        "riskPips": 22.2,
        "rrRatio": 1.2,
        "setupType": "Liquidity Sweep Reversal (Test Alert)",
        "reason": "Test Alert: Sell-side liquidity pool raid on GBPUSD 15m with strong bullish rejection wick.",
        "timestamp": now_utc.isoformat(),
        "isTest": True,
    }

    # Add to recent alerts
    trading_runner.recent_alerts.insert(0, mock_alert)
    if len(trading_runner.recent_alerts) > 50:
        trading_runner.recent_alerts.pop()

    # Broadcast to connected clients
    trading_runner.broadcast_notification("notifications", "liquidity_alert", mock_alert)

    return {
        "status": "ok",
        "message": "Test notification dispatched successfully",
        "alert": mock_alert,
    }
