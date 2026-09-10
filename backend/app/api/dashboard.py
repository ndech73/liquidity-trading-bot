from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models.trade import TradeModel
from app.execution.mt5_executor import MT5Executor

router = APIRouter()


@router.get("/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Computes real dashboard statistics from MT5 and persistent DB records."""
    open_trades = db.query(TradeModel).filter_by(status="OPEN").all()
    open_lots = sum(t.lots for t in open_trades) if open_trades else 0.0
    unrealized_pnl = sum(t.profit for t in open_trades) if open_trades else 0.0

    # Today's realized PnL from closed trades
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_closed = (
        db.query(TradeModel)
        .filter(TradeModel.status == "CLOSED", TradeModel.closed_at >= today_start)
        .all()
    )
    realized_today = sum(t.profit for t in today_closed) if today_closed else 0.0
    winning_today = sum(1 for t in today_closed if t.profit > 0)
    win_rate_today = (winning_today / len(today_closed) * 100) if today_closed else 0.0

    balance = 0.0
    equity = 0.0

    try:
        executor = MT5Executor()
        if executor.connect():
            info = executor.get_account_info()
            if info:
                balance = float(getattr(info, "balance", 0.0))
                equity = float(getattr(info, "equity", 0.0))
            executor.close()
    except Exception:
        pass

    return {
        "equity": round(equity, 2),
        "balance": round(balance, 2),
        "unrealizedPnL": round(unrealized_pnl, 2),
        "realizedPnLToday": round(realized_today, 2),
        "activeTradesCount": len(open_trades),
        "winRateToday": round(win_rate_today, 1),
        "openLots": round(open_lots, 2),
    }


@router.get("/dashboard/daily")
def get_daily_performance(db: Session = Depends(get_db)):
    """Aggregates real daily PnL and trade count for the past 7 days from the database."""
    now = datetime.now(timezone.utc)
    daily_records = []

    for i in range(6, -1, -1):
        day_date = now - timedelta(days=i)
        day_start = day_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_name = day_date.strftime("%a")

        trades = (
            db.query(TradeModel)
            .filter(
                TradeModel.status == "CLOSED",
                TradeModel.closed_at >= day_start,
                TradeModel.closed_at < day_end,
            )
            .all()
        )

        pnl = sum(t.profit for t in trades) if trades else 0.0
        daily_records.append({
            "date": day_name,
            "pnl": round(pnl, 2),
            "tradesCount": len(trades),
        })

    return daily_records


@router.get("/dashboard/equity-curve")
def get_equity_curve(db: Session = Depends(get_db)):
    """Computes equity progression points over time from closed trades and live MT5 equity."""
    current_balance = 0.0
    current_equity = 0.0
    try:
        executor = MT5Executor()
        if executor.connect():
            info = executor.get_account_info()
            if info:
                current_balance = float(getattr(info, "balance", 0.0))
                current_equity = float(getattr(info, "equity", 0.0))
            executor.close()
    except Exception:
        pass

    closed_trades = (
        db.query(TradeModel)
        .filter(TradeModel.status == "CLOSED", TradeModel.closed_at.isnot(None))
        .order_by(TradeModel.closed_at.asc())
        .all()
    )

    total_profit = sum(t.profit for t in closed_trades) if closed_trades else 0.0
    starting_balance = max(0.0, round(current_balance - total_profit, 2))

    points = []
    now = datetime.now(timezone.utc)

    if not closed_trades:
        baseline_equity = current_equity if current_equity > 0 else (current_balance if current_balance > 0 else 0.0)
        for hours_ago in [24, 18, 12, 6, 2, 0]:
            pt_time = now - timedelta(hours=hours_ago)
            points.append({
                "time": int(pt_time.timestamp()),
                "value": round(baseline_equity, 2),
            })
    else:
        cum_equity = starting_balance
        first_time = closed_trades[0].closed_at or (now - timedelta(days=1))
        points.append({
            "time": int((first_time - timedelta(hours=1)).timestamp()),
            "value": round(cum_equity, 2),
        })
        for t in closed_trades:
            cum_equity += t.profit
            points.append({
                "time": int(t.closed_at.timestamp()),
                "value": round(cum_equity, 2),
            })

        points.append({
            "time": int(now.timestamp()),
            "value": round(current_equity if current_equity > 0 else cum_equity, 2),
        })

    return points
