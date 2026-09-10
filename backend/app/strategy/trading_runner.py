"""
Live automated trading runner and background engine.

1. Synchronizes open positions and closed trades between MT5 and PostgreSQL.
2. Pulls recent M5 candles for each symbol in the watchlist.
3. Analyzes liquidity zones, sweep events, volatility, compression, and expansion via AnalysisEngine.
4. Persists liquidity zones, sweep breach events, and snapshots to PostgreSQL so the dashboard displays live market structure.
5. Evaluates actionable entry signals with EntryEngine.
6. Filters setups for freshness, trend alignment, and price validity.
7. Computes fixed risk:reward exit levels (SL / TP) via ExitEngine.
8. Evaluates capital exposure, account margin, and lot sizing via RiskEngine.
9. Automatically executes live market orders on MT5 when setups qualify.
10. Broadcasts trade updates via WebSockets for instant dashboard visualization.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional
from loguru import logger
from sqlalchemy.orm import Session

from app.analysis_engine.domain.candle import Candle, Timeframe
from app.analysis_engine.domain.liquidity import LiquidityZone
from app.analysis_engine.engine import AnalysisEngine, MarketSnapshot
from app.core.settings import get_settings
from app.db.models.event import LiquiditySweepEventModel
from app.db.models.snapshot import MarketSnapshotModel
from app.db.models.trade import TradeModel
from app.db.models.zone import LiquidityZoneModel
from app.db.session import SessionLocal
from app.execution.mt5_executor import MT5Executor
from app.risk.risk_engine import RiskEngine
from app.strategy.entry_engine import EntryEngine, EntrySignal, TradeDirection
from app.strategy.exit_engine import ExitEngine


WATCHLIST = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP",
]


class TradingRunner:
    def __init__(
        self,
        watchlist: list[str] | None = None,
        timeframe: Timeframe = Timeframe.M5,
        candle_count: int = 120,
        positions_per_trade: int = 2,
        max_signal_age_candles: int = 6,
        risk_engine: RiskEngine | None = None,
        entry_engine: EntryEngine | None = None,
        exit_engine: ExitEngine | None = None,
        poll_interval_seconds: float = 10.0,
    ) -> None:
        self.watchlist = watchlist or list(WATCHLIST)
        self.timeframe = timeframe
        self.candle_count = candle_count
        self.positions_per_trade = positions_per_trade
        self.max_signal_age_candles = max_signal_age_candles
        self.risk_engine = risk_engine or RiskEngine(
            default_lot_size=0.05,
            min_lot_size=0.05,
            max_open_trades=10,
            max_trades_per_symbol=2,
        )
        self.entry_engine = entry_engine or EntryEngine(allow_ranging_trend=True, require_expansion=True)
        self.exit_engine = exit_engine or ExitEngine(risk_reward_ratio=3.0, take_profit_pips=None)
        self.analysis_engine = AnalysisEngine()
        self.poll_interval_seconds = poll_interval_seconds

        self.executor = MT5Executor()
        self.tracked_zones: dict[str, list[LiquidityZone]] = {s: [] for s in self.watchlist}
        self.executed_setup_keys: set[str] = set()
        self._is_running = False

    async def run(self) -> None:
        """Main background loop."""
        self._is_running = True
        logger.info("[TradingRunner] Automated trading runner started.")
        while self._is_running:
            try:
                await asyncio.to_thread(self.cycle)
            except Exception as e:
                logger.error(f"[TradingRunner] Unhandled error during trading cycle: {e}")
            await asyncio.sleep(self.poll_interval_seconds)

    def stop(self) -> None:
        self._is_running = False
        logger.info("[TradingRunner] Stopping automated trading runner...")

    def cycle(self) -> None:
        """Executes a single scan, sync, and trading cycle synchronously."""
        # 1. Connect to MT5 if needed
        try:
            if not self.executor.connect():
                logger.warning("[TradingRunner] MT5 connection not ready, skipping cycle.")
                return
        except Exception as e:
            logger.warning(f"[TradingRunner] Could not connect to MT5: {e}")
            return

        # 2. Synchronize open & closed positions with DB
        self.sync_positions()

        # 3. Fetch account info
        try:
            acc_info = self.executor.get_account_info()
            if not acc_info:
                return
            account_dict = {
                "balance": float(getattr(acc_info, "balance", 0.0)),
                "margin_free": float(getattr(acc_info, "margin_free", getattr(acc_info, "balance", 0.0))),
                "equity": float(getattr(acc_info, "equity", 0.0)),
            }
        except Exception as e:
            logger.warning(f"[TradingRunner] Could not fetch account info: {e}")
            return

        # 4. Fetch current open positions from MT5
        open_positions = self.executor.get_positions()
        open_symbols = {p["symbol"].upper() for p in open_positions}

        # Also get symbols with OPEN trades in DB
        db: Session = SessionLocal()
        try:
            db_open_trades = db.query(TradeModel).filter_by(status="OPEN").all()
            for t in db_open_trades:
                open_symbols.add(t.symbol.upper())
        except Exception as e:
            logger.warning(f"[TradingRunner] Error querying DB open trades: {e}")
        finally:
            db.close()

        # Check max open trades
        if len(open_positions) >= self.risk_engine.max_open_trades:
            logger.debug(f"[TradingRunner] Max open trades ({self.risk_engine.max_open_trades}) reached. Skipping new entries.")
            scan_for_entries = False
        else:
            scan_for_entries = True

        # 5. Loop through watchlist
        for symbol in self.watchlist:
            try:
                self.process_symbol(
                    symbol=symbol,
                    account_dict=account_dict,
                    open_positions=open_positions,
                    open_symbols=open_symbols,
                    scan_for_entries=scan_for_entries,
                )
            except Exception as e:
                logger.error(f"[TradingRunner] Error processing {symbol}: {e}")

    def sync_positions(self) -> None:
        """Syncs open positions in MT5 against DB records, detecting closures and realized PnL."""
        db: Session = SessionLocal()
        try:
            open_positions = self.executor.get_positions()
            mt5_tickets = {p["ticket"]: p for p in open_positions}

            db_open_trades = db.query(TradeModel).filter_by(status="OPEN").all()
            for trade in db_open_trades:
                if trade.ticket in mt5_tickets:
                    # Trade is still active on MT5 - update unrealized profit and current price
                    pos = mt5_tickets[trade.ticket]
                    trade.profit = pos.get("profit", trade.profit)
                    trade.close_price = pos.get("price_current", trade.close_price)
                else:
                    # Trade was closed on MT5!
                    deals = self.executor.get_position_deals(trade.ticket)
                    exit_deal = None
                    for d in deals:
                        if d.get("entry") == 1:  # ENTRY_OUT
                            exit_deal = d
                            break

                    trade.status = "CLOSED"
                    trade.closed_at = datetime.now(timezone.utc)
                    if exit_deal:
                        trade.close_price = exit_deal.get("price", trade.close_price or trade.open_price)
                        trade.profit = round(exit_deal.get("profit", 0.0) + exit_deal.get("swap", 0.0) + exit_deal.get("commission", 0.0), 2)
                    logger.success(
                        f"[TradingRunner] Position {trade.ticket} ({trade.symbol}) closed. Final profit: ${trade.profit:.2f}"
                    )
            db.commit()
        except Exception as e:
            logger.warning(f"[TradingRunner] Error during position sync: {e}")
            db.rollback()
        finally:
            db.close()

    def process_symbol(
        self,
        symbol: str,
        account_dict: dict,
        open_positions: list,
        open_symbols: set,
        scan_for_entries: bool,
    ) -> None:
        """Fetches candles, analyzes structure, persists to DB, and executes qualifying signals."""
        candles = self.executor.fetch_candles(symbol, self.timeframe, self.candle_count)
        if not candles or len(candles) < 30:
            return

        # 1. Run Analysis Pipeline
        existing = self.tracked_zones.get(symbol, [])
        snapshot = self.analysis_engine.analyze(candles, existing_zones=existing)
        self.tracked_zones[symbol] = snapshot.zones

        # 2. Persist zones, sweeps, and snapshot to DB
        self._persist_analysis(symbol, candles, snapshot)

        # 3. Check if we should evaluate and open trades
        if not scan_for_entries or symbol.upper() in open_symbols:
            return

        # 4. Generate entry signals
        signals = self.entry_engine.evaluate(snapshot, candles)
        if not signals:
            return

        # 5. Find qualifying signal
        for signal in signals:
            # Check setup recency (e.g. occurred within the last 12 M5 candles ~ 1 hour)
            signal_candle_idx = None
            for idx, c in enumerate(candles):
                if c.timestamp == signal.signal_time:
                    signal_candle_idx = idx
                    break

            if signal_candle_idx is not None:
                candle_age = len(candles) - 1 - signal_candle_idx
                if candle_age > self.max_signal_age_candles:
                    continue  # Stale setup

            setup_key = f"{signal.symbol}_{signal.zone_id}_{signal.signal_time.isoformat()}"
            if setup_key in self.executed_setup_keys:
                continue

            # Check price validity against current tick
            exits = self.exit_engine.compute_exit_levels(signal)
            tick = None
            try:
                tick = self.executor.mt5.symbol_info_tick(signal.symbol)
            except Exception:
                pass

            if not tick:
                continue

            current_price = float(tick.ask if signal.direction == TradeDirection.BUY else tick.bid)
            if signal.direction == TradeDirection.BUY:
                if current_price <= exits.stop_loss or current_price >= exits.take_profit:
                    continue  # Invalid: already hit SL or TP
            else:
                if current_price >= exits.stop_loss or current_price <= exits.take_profit:
                    continue  # Invalid: already hit SL or TP

            # 6. Risk Check (refresh real-time free margin)
            try:
                acc_now = self.executor.get_account_info()
                if acc_now:
                    account_dict["margin_free"] = float(getattr(acc_now, "margin_free", account_dict.get("margin_free", 0.0)))
                    account_dict["balance"] = float(getattr(acc_now, "balance", account_dict.get("balance", 0.0)))
            except Exception:
                pass

            risk_res = self.risk_engine.check(
                signal=signal,
                account=account_dict,
                open_positions=open_positions,
            )
            if not risk_res.approved:
                logger.info(f"[TradingRunner] Signal for {signal.symbol} rejected by risk engine: {risk_res.reason}")
                continue

            # 7. Execute live orders on MT5 (2 positions per trade setup)
            opened_any = False
            for pos_num in range(1, self.positions_per_trade + 1):
                try:
                    acc_check = self.executor.get_account_info()
                    if acc_check is not None:
                        free_val = getattr(acc_check, "margin_free", None)
                        if free_val is not None and isinstance(free_val, (int, float)) and free_val < 2.0:
                            logger.warning(f"[TradingRunner] Insufficient free margin for position {pos_num}/{self.positions_per_trade}. Skipping.")
                            break
                except Exception:
                    pass

                comment_tag = f"LiquidityBot P{pos_num}"
                logger.info(
                    f"[TradingRunner] Executing {signal.direction.value.upper()} position {pos_num}/{self.positions_per_trade} "
                    f"on {signal.symbol} ({risk_res.lot_size} lots) | SL={exits.stop_loss:.5f} | TP={exits.take_profit:.5f}"
                )
                order_res = self.executor.open_order(
                    symbol=signal.symbol,
                    order_type=signal.direction.value,
                    volume=risk_res.lot_size,
                    stop_loss=exits.stop_loss,
                    take_profit=exits.take_profit,
                    comment=comment_tag,
                )

                if order_res.get("success"):
                    opened_any = True
                    ticket = order_res.get("ticket")
                    fill_price = order_res.get("price", current_price)

                    # Persist to DB
                    db: Session = SessionLocal()
                    try:
                        new_trade = TradeModel(
                            ticket=ticket,
                            symbol=signal.symbol,
                            order_type=signal.direction.value.upper(),
                            lots=risk_res.lot_size,
                            open_price=fill_price,
                            stop_loss=exits.stop_loss,
                            take_profit=exits.take_profit,
                            profit=0.0,
                            status="OPEN",
                            opened_at=datetime.now(timezone.utc),
                        )
                        db.add(new_trade)
                        db.commit()
                        logger.success(
                            f"[TradingRunner] Opened position {pos_num}/{self.positions_per_trade} "
                            f"(Ticket #{ticket}) on {signal.symbol} ({risk_res.lot_size} lots)!"
                        )
                    except Exception as e:
                        logger.error(f"[TradingRunner] Error saving trade to DB: {e}")
                        db.rollback()
                    finally:
                        db.close()
                else:
                    logger.warning(
                        f"[TradingRunner] Position {pos_num}/{self.positions_per_trade} failed on {signal.symbol}: "
                        f"{order_res.get('error')}"
                    )

            if opened_any:
                self.executed_setup_keys.add(setup_key)
                open_symbols.add(signal.symbol.upper())
                break  # Setup executed with 3 positions

    def _persist_analysis(self, symbol: str, candles: list[Candle], snapshot: MarketSnapshot) -> None:
        """Persists detected liquidity zones, sweeps, and market snapshot into PostgreSQL."""
        db: Session = SessionLocal()
        try:
            # 1. Persist/update Liquidity Zones
            for z in snapshot.zones:
                existing_zone = db.query(LiquidityZoneModel).filter_by(id=z.id).first()
                if existing_zone:
                    existing_zone.status = z.status.value
                    existing_zone.touches = z.touches
                    existing_zone.swept_at = z.swept_at
                    existing_zone.sweep_price = z.sweep_price
                else:
                    db_zone = LiquidityZoneModel(
                        id=z.id,
                        symbol=symbol.upper(),
                        timeframe="5m",
                        side=z.side.value,
                        liquidity_type=z.liquidity_type.value,
                        price=z.price,
                        status=z.status.value,
                        touches=z.touches,
                        created_at=z.created_at,
                        swept_at=z.swept_at,
                        sweep_price=z.sweep_price,
                    )
                    db.add(db_zone)

            # 2. Persist Sweep Events
            for ev in snapshot.sweep_events:
                existing_event = (
                    db.query(LiquiditySweepEventModel)
                    .filter_by(zone_id=ev.zone_id, occurred_at=ev.occurred_at)
                    .first()
                )
                if not existing_event:
                    db_event = LiquiditySweepEventModel(
                        zone_id=ev.zone_id,
                        symbol=symbol.upper(),
                        timeframe="5m",
                        side=ev.side.value,
                        liquidity_type=ev.liquidity_type.value,
                        level_price=ev.level_price,
                        sweep_price=ev.sweep_price,
                        detected_via=ev.detected_via,
                        occurred_at=ev.occurred_at,
                    )
                    db.add(db_event)

            # 3. Persist latest Market Snapshot
            vol_regime = snapshot.volatility.regime.value if snapshot.volatility else "NORMAL"
            atr_val = snapshot.volatility.atr if snapshot.volatility else None
            is_comp = snapshot.compression.is_compressed if snapshot.compression else False
            is_exp = snapshot.expansion.is_expanding if snapshot.expansion else False

            latest_snap = (
                db.query(MarketSnapshotModel)
                .filter_by(symbol=symbol.upper())
                .order_by(MarketSnapshotModel.recorded_at.desc())
                .first()
            )

            now_utc = datetime.now(timezone.utc)
            if not latest_snap or (now_utc - latest_snap.recorded_at).total_seconds() >= 300:
                snap_rec = MarketSnapshotModel(
                    symbol=symbol.upper(),
                    timeframe="5m",
                    candles_analyzed=len(candles),
                    atr=atr_val,
                    volatility_regime=vol_regime,
                    is_compressed=is_comp,
                    is_expanded=is_exp,
                    recorded_at=now_utc,
                )
                db.add(snap_rec)
            else:
                latest_snap.atr = atr_val
                latest_snap.volatility_regime = vol_regime
                latest_snap.is_compressed = is_comp
                latest_snap.is_expanded = is_exp

            db.commit()
        except Exception as e:
            db.rollback()
            logger.debug(f"[TradingRunner] Could not persist analysis for {symbol}: {e}")
        finally:
            db.close()


trading_runner = TradingRunner()


async def trading_bot_worker() -> None:
    """Entry point for the FastAPI lifespan task."""
    await trading_runner.run()
