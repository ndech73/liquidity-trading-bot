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
        min_lot_size: float = 0.01,
        max_lot_size: float = 1.0,
        default_lot_size: float = 0.01,
        max_setup_risk_usd: float | None = None,
        positions_per_trade: int = 2,
    ) -> None:
        settings = None
        try:
            from app.core.settings import get_settings
            settings = get_settings().analysis
        except Exception:
            pass

        self.max_open_trades = max_open_trades
        self.max_trades_per_symbol = max_trades_per_symbol
        self.risk_per_trade_pct = risk_per_trade_pct
        self.min_lot_size = min_lot_size
        self.max_lot_size = max_lot_size
        self.default_lot_size = default_lot_size
        self.positions_per_trade = positions_per_trade
        self.max_setup_risk_usd = (
            max_setup_risk_usd
            if max_setup_risk_usd is not None
            else (getattr(settings, "max_setup_risk_usd", 3.50) if settings else 3.50)
        )

    @staticmethod
    def estimate_pip_value_usd(symbol: str) -> float:
        """Estimates USD pip value for 1.0 standard lot."""
        s = symbol.upper()
        if "JPY" in s:
            return 6.5
        if s.endswith("CHF") or "CHF" in s:
            return 12.2
        if s.endswith("GBP") or "GBP" in s:
            return 13.4
        if s.endswith("CAD") or "CAD" in s:
            return 7.2
        return 10.0

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

        # 5. Dynamic Position Sizing & Hard Setup Dollar Risk Cap
        is_jpy = "JPY" in symbol.upper()
        pip_size = 0.01 if is_jpy else 0.0001
        pips_at_risk = sl_dist / pip_size
        pip_value_usd = self.estimate_pip_value_usd(symbol)

        # Dynamic lot sizing: calculate lot size per position such that total setup risk <= max_setup_risk_usd
        if self.max_setup_risk_usd and self.max_setup_risk_usd > 0 and pips_at_risk > 0 and pip_value_usd > 0:
            target_risk = self.max_setup_risk_usd
            if balance > 50.0:
                target_risk = min(self.max_setup_risk_usd, balance * self.risk_per_trade_pct * self.positions_per_trade)
            ideal_lot = target_risk / (pips_at_risk * pip_value_usd * self.positions_per_trade)
            # Floor to 2 decimal places so we never round up and exceed risk
            computed_lot = max(self.min_lot_size, min(float(int(ideal_lot * 100) / 100.0), self.max_lot_size))
        else:
            computed_lot = self.default_lot_size

        single_risk_amount = round(pips_at_risk * pip_value_usd * computed_lot, 2)
        total_setup_risk = round(single_risk_amount * self.positions_per_trade, 2)

        # Hard dollar risk guard across all setup positions
        if self.max_setup_risk_usd and self.max_setup_risk_usd > 0:
            if total_setup_risk > self.max_setup_risk_usd + 0.05:
                return RiskAssessment(
                    approved=False,
                    reason=(
                        f"Setup risk (${total_setup_risk:.2f}) exceeds max allowed "
                        f"risk (${self.max_setup_risk_usd:.2f}) across {self.positions_per_trade} "
                        f"positions ({pips_at_risk:.1f} pips SL)"
                    ),
                    lot_size=computed_lot,
                    risk_amount=single_risk_amount,
                )

        return RiskAssessment(
            approved=True,
            reason="Approved",
            lot_size=computed_lot,
            risk_amount=single_risk_amount,
        )
