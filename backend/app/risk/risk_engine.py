from dataclasses import dataclass
from typing import Optional, Dict, Any
from loguru import logger


@dataclass(frozen=True)
class RiskAssessment:
    approved: bool
    reason: str
    lot_size: float = 0.01
    risk_amount: float = 0.0


class RiskEngine:
    """Evaluates entry signals against account capital, margin limits, and exposure."""

    def __init__(
        self,
        max_open_trades: int = 10,
        max_trades_per_symbol: int = 2,
        risk_per_trade_pct: float = 0.01,
        min_lot_size: float = 0.05,
        max_lot_size: float = 1.0,
        default_lot_size: float = 0.05,
    ) -> None:
        self.max_open_trades = max_open_trades
        self.max_trades_per_symbol = max_trades_per_symbol
        self.risk_per_trade_pct = risk_per_trade_pct
        self.min_lot_size = min_lot_size
        self.max_lot_size = max_lot_size
        self.default_lot_size = default_lot_size

    def check(
        self,
        signal: Any,
        account: Dict[str, Any],
        open_positions: list = None,
    ) -> RiskAssessment:
        open_positions = open_positions or []
        symbol = getattr(signal, "symbol", signal.get("symbol") if isinstance(signal, dict) else "")
        entry_price = float(getattr(signal, "entry_price", signal.get("entry_price", 0.0) if isinstance(signal, dict) else 0.0))
        stop_loss = float(getattr(signal, "stop_loss", signal.get("stop_loss", 0.0) if isinstance(signal, dict) else 0.0))

        # 1. Check account balance and free margin
        balance = float(account.get("balance", 0.0))
        free_margin = float(account.get("margin_free", account.get("balance", 0.0)))
        if free_margin <= 0.5:
            return RiskAssessment(
                approved=False,
                reason=f"Insufficient free margin (${free_margin:.2f})",
            )

        # 2. Check maximum concurrent open trades
        if len(open_positions) >= self.max_open_trades:
            return RiskAssessment(
                approved=False,
                reason=f"Max open trades reached ({len(open_positions)}/{self.max_open_trades})",
            )

        # 3. Check exposure on this symbol
        matching_symbol_trades = [
            p for p in open_positions if getattr(p, "symbol", p.get("symbol") if isinstance(p, dict) else "") == symbol
        ]
        if len(matching_symbol_trades) >= self.max_trades_per_symbol:
            return RiskAssessment(
                approved=False,
                reason=f"Max trades reached for symbol {symbol}",
            )

        # 4. Validate stop loss distance
        sl_dist = abs(entry_price - stop_loss)
        if sl_dist <= 0:
            return RiskAssessment(
                approved=False,
                reason="Invalid stop loss: distance to entry is zero",
            )

        # 5. Position Sizing
        # For small demo accounts (e.g. < $50), safely trade minimum lot size (0.01 lot)
        computed_lot = self.default_lot_size
        if balance > 50.0:
            risk_capital = balance * self.risk_per_trade_pct
            # 1 standard lot = 100,000 units, roughly $10/pip for EUR/USD
            pip_size = 0.0001
            pips_at_risk = sl_dist / pip_size
            if pips_at_risk > 0:
                raw_lots = risk_capital / (pips_at_risk * 10.0)
                computed_lot = max(self.min_lot_size, min(round(raw_lots, 2), self.max_lot_size))

        risk_amount = round(sl_dist * 100000 * computed_lot, 2)

        return RiskAssessment(
            approved=True,
            reason="Approved",
            lot_size=computed_lot,
            risk_amount=risk_amount,
        )
