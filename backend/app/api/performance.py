from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.trade import TradeModel

router = APIRouter()


@router.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    """Computes real performance metrics from closed trades in the database."""
    closed_trades = db.query(TradeModel).filter_by(status="CLOSED").all()

    total_profit = sum(t.profit for t in closed_trades) if closed_trades else 0.0
    wins = [t.profit for t in closed_trades if t.profit > 0]
    losses = [abs(t.profit) for t in closed_trades if t.profit < 0]

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = sum(losses) if losses else 0.0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (1.0 if gross_profit > 0 else 0.0)
    win_rate = round((len(wins) / len(closed_trades)) * 100, 1) if closed_trades else 0.0

    win_count = len(wins)
    loss_count = len(losses)
    avg_win = round(gross_profit / win_count, 2) if win_count > 0 else 0.0
    avg_loss = round(gross_loss / loss_count, 2) if loss_count > 0 else 0.0

    daily_map = {}
    for t in closed_trades:
        if t.closed_at:
            day_str = t.closed_at.strftime("%Y-%m-%d")
            if day_str not in daily_map:
                daily_map[day_str] = {"pnl": 0.0, "trades": 0}
            daily_map[day_str]["pnl"] += t.profit
            daily_map[day_str]["trades"] += 1

    daily_pnl = [
        {"date": d, "pnl": round(data["pnl"], 2), "tradesCount": data["trades"]}
        for d, data in sorted(daily_map.items(), reverse=True)
    ]

    metrics = [
        {
            "label": "Total Net Profit",
            "value": f"${total_profit:,.2f}" if total_profit >= 0 else f"-${abs(total_profit):,.2f}",
            "isPositive": total_profit >= 0,
        },
        {
            "label": "Profit Factor",
            "value": f"{profit_factor:.2f}",
            "isPositive": profit_factor >= 1.0,
        },
        {
            "label": "Win Rate",
            "value": f"{win_rate:.1f}%",
            "isPositive": win_rate >= 50.0,
        },
        {
            "label": "Total Closed Trades",
            "value": str(len(closed_trades)),
            "isPositive": len(closed_trades) > 0,
        },
    ]

    return {
        "metrics": metrics,
        "winCount": win_count,
        "lossCount": loss_count,
        "avgWin": avg_win,
        "avgLoss": avg_loss,
        "dailyPnl": daily_pnl,
        "totalTrades": len(closed_trades),
    }

