from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.trade import TradeModel
from app.execution.mt5_executor import MT5Executor

router = APIRouter()


@router.get("/trades")
def get_trades(db: Session = Depends(get_db)):
    """Returns real active open positions from MT5 or persistent database."""
    trades = []

    # 1. Try fetching live open positions directly from MT5
    try:
        executor = MT5Executor()
        if executor.connect():
            positions = executor.get_positions()
            for pos in positions:
                p_type = pos.get("type", 0) if isinstance(pos, dict) else getattr(pos, "type", 0)
                pos_type = "BUY" if p_type == 0 else "SELL"
                p_time = int((pos.get("time") if isinstance(pos, dict) else getattr(pos, "time", 0)) or 0)
                open_time = datetime.fromtimestamp(
                    p_time, tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S") if p_time > 0 else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                p_ticket = int((pos.get("ticket") if isinstance(pos, dict) else getattr(pos, "ticket", 0)) or 0)
                p_symbol = str((pos.get("symbol") if isinstance(pos, dict) else getattr(pos, "symbol", "")) or "")
                p_volume = float((pos.get("volume") if isinstance(pos, dict) else getattr(pos, "volume", 0.0)) or 0.0)
                p_open = float((pos.get("price_open") if isinstance(pos, dict) else getattr(pos, "price_open", 0.0)) or 0.0)
                p_current = float((pos.get("price_current") if isinstance(pos, dict) else getattr(pos, "price_current", 0.0)) or p_open)
                p_sl = float((pos.get("sl") if isinstance(pos, dict) else getattr(pos, "sl", 0.0)) or 0.0)
                p_tp = float((pos.get("tp") if isinstance(pos, dict) else getattr(pos, "tp", 0.0)) or 0.0)
                p_profit = round(float((pos.get("profit") if isinstance(pos, dict) else getattr(pos, "profit", 0.0)) or 0.0), 2)

                trades.append({
                    "id": f"mt5-{p_ticket}",
                    "ticket": p_ticket,
                    "symbol": p_symbol,
                    "type": pos_type,
                    "lots": p_volume,
                    "openPrice": p_open,
                    "currentPrice": p_current,
                    "stopLoss": p_sl,
                    "takeProfit": p_tp,
                    "profit": p_profit,
                    "openTime": open_time,
                })
            executor.close()
    except Exception:
        pass

    # 2. If MT5 returned positions, return them; otherwise check persistent DB for OPEN trades
    if not trades:
        try:
            db_trades = db.query(TradeModel).filter_by(status="OPEN").all()
            for t in db_trades:
                trades.append({
                    "id": t.id,
                    "ticket": t.ticket,
                    "symbol": t.symbol,
                    "type": t.order_type,
                    "lots": t.lots,
                    "openPrice": t.open_price,
                    "currentPrice": t.close_price or t.open_price,
                    "stopLoss": t.stop_loss or 0.0,
                    "takeProfit": t.take_profit or 0.0,
                    "profit": t.profit,
                    "openTime": t.opened_at.strftime("%Y-%m-%d %H:%M:%S"),
                })
        except Exception as e:
            pass

    return trades


@router.get("/trades/history")
def get_trade_history(db: Session = Depends(get_db)):
    """Returns closed trade records from the database."""
    try:
        history = db.query(TradeModel).filter_by(status="CLOSED").order_by(TradeModel.closed_at.desc()).limit(100).all()
        return [
            {
                "id": t.id,
                "ticket": t.ticket,
                "symbol": t.symbol,
                "type": t.order_type,
                "lots": t.lots,
                "openPrice": t.open_price,
                "closePrice": t.close_price or 0.0,
                "profit": t.profit,
                "status": t.status,
                "openedAt": t.opened_at.isoformat(),
                "closedAt": t.closed_at.isoformat() if t.closed_at else None,
            }
            for t in history
        ]
    except Exception as e:
        return []
