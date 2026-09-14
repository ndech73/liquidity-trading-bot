from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db, check_db_connection
from app.db.models.trade import TradeModel
from app.execution.mt5_executor import MT5Executor

router = APIRouter()


@router.get("/account")
def get_account(db: Session = Depends(get_db)):
    """Returns live account metrics from MT5 or persistent state."""
    # Calculate open metrics from DB if MT5 isn't initialized with credentials
    open_trades = []
    open_pnl = 0.0
    try:
        open_trades = db.query(TradeModel).filter_by(status="OPEN").all()
        open_pnl = sum(t.profit for t in open_trades) if open_trades else 0.0
    except Exception:
        pass

    account_data = {
        "login": None,
        "balance": 0.0,
        "equity": 0.0,
        "currency": "USD",
        "connected": False,
        "status": "OFFLINE",
        "open_trades_count": len(open_trades),
        "unrealized_pnl": round(open_pnl, 2),
    }

    try:
        executor = MT5Executor()
        if executor.connect():
            info = executor.get_account_info()
            if info:
                account_data["login"] = getattr(info, "login", None)
                account_data["balance"] = float(getattr(info, "balance", 0.0))
                account_data["equity"] = float(getattr(info, "equity", 0.0))
                account_data["currency"] = getattr(info, "currency", "USD")
                account_data["connected"] = True
                account_data["status"] = "RUNNING"
            executor.close()
    except Exception:
        # Fall back to base state when MT5 terminal credentials are not configured
        pass

    return account_data
