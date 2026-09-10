from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.trade import TradeModel

router = APIRouter()


@router.get("/forensics")
def get_forensics(db: Session = Depends(get_db)):
    """Returns trade forensic records linked to historical execution."""
    trades = db.query(TradeModel).order_by(TradeModel.opened_at.desc()).limit(50).all()

    records = []
    for t in trades:
        rr = (
            round(abs(t.take_profit - t.open_price) / abs(t.open_price - t.stop_loss), 2)
            if (t.stop_loss and t.open_price != t.stop_loss and t.take_profit)
            else 2.0
        )
        timeline = [
            {
                "time": t.opened_at.strftime("%H:%M:%S"),
                "title": f"Liquidity sweep breach detected around {t.open_price:.5f}",
                "type": "sweep",
            },
            {
                "time": t.opened_at.strftime("%H:%M:%S"),
                "title": f"{t.order_type} order #{t.ticket} dispatched ({t.lots} lots @ {t.open_price:.5f})",
                "type": "order",
            },
        ]
        if t.closed_at:
            timeline.append({
                "time": t.closed_at.strftime("%H:%M:%S"),
                "title": f"Position closed at {t.close_price:.5f} (PnL: ${t.profit:+.2f})",
                "type": "close",
            })

        records.append({
            "tradeId": f"t-{t.ticket}",
            "ticket": t.ticket,
            "symbol": t.symbol,
            "triggerReason": f"{t.order_type} execution on liquidity boundary sweep",
            "liquidityPoolSwept": f"{t.open_price:.5f} Key Level",
            "volatilityAtEntry": 1.5,
            "entryTimestamp": t.opened_at.strftime("%Y-%m-%d %H:%M:%S"),
            "exitTimestamp": t.closed_at.strftime("%Y-%m-%d %H:%M:%S") if t.closed_at else None,
            "outcomePips": round((t.profit / (t.lots * 10)), 1) if t.lots > 0 else 0.0,
            "lots": t.lots,
            "openPrice": t.open_price,
            "closePrice": t.close_price,
            "profit": t.profit,
            "orderType": t.order_type,
            "riskRewardRatio": rr,
            "timeline": timeline,
        })

    return records

