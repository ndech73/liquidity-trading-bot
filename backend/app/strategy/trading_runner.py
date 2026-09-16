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
from app.analysis_engine.liquidity.sweep_detector import SweepDetector
from app.core.settings import get_settings
from app.db.models.event import LiquiditySweepEventModel
from app.core.settings import PRODUCTION_WATCHLIST
from app.db.models.snapshot import MarketSnapshotModel
from app.db.models.trade import TradeModel
from app.db.models.zone import LiquidityZoneModel
from app.db.session import SessionLocal
from app.execution.mt5_executor import MT5Executor
from app.risk.risk_engine import RiskEngine
from app.strategy.entry_engine import EntryEngine, EntrySignal, TradeDirection
from app.strategy.exit_engine import ExitEngine


WATCHLIST = PRODUCTION_WATCHLIST


class TradingRunner:
    def __init__(
        self,
        watchlist: list[str] | None = None,
        timeframe: Timeframe = Timeframe.M15,
        htf_timeframe: Timeframe = Timeframe.H1,
        candle_count: int = 250,
        positions_per_trade: int = 2,
        max_signal_age_candles: int = 2,
        breakeven_pips: float | None = None,
        breakeven_buffer_pips: float | None = None,
        tp1_rr: float = 1.2,
        tp2_rr: float = 3.0,
        enable_friday_close: bool = True,
        friday_close_hour_utc: int = 20,
        enable_session_filter: bool = True,
        session_start_hour_utc: int = 7,
        session_end_hour_utc: int = 18,
        risk_engine: RiskEngine | None = None,
        entry_engine: EntryEngine | None = None,
        exit_engine: ExitEngine | None = None,
        poll_interval_seconds: float = 10.0,
        htf_alignment_symbols: list[str] | None = None,
        max_stop_loss_pips: float = 18.0,
    ) -> None:
        self.watchlist = watchlist or list(WATCHLIST)
        self.htf_alignment_symbols = [s.upper() for s in htf_alignment_symbols] if htf_alignment_symbols is not None else None
        self.timeframe = timeframe
        self.htf_timeframe = htf_timeframe
        self.candle_count = candle_count
        self.positions_per_trade = positions_per_trade
        self.max_signal_age_candles = max_signal_age_candles

        settings = None
        try:
            settings = get_settings().analysis
        except Exception:
            pass

        self.breakeven_pips = (
            breakeven_pips
            if breakeven_pips is not None
            else (getattr(settings, "early_breakeven_trigger_pips", 15.0) if settings else 15.0)
        )
        self.breakeven_buffer_pips = (
            breakeven_buffer_pips
            if breakeven_buffer_pips is not None
            else (getattr(settings, "early_breakeven_buffer_pips", 3.0) if settings else 3.0)
        )
        self.tp1_rr = tp1_rr
        self.tp2_rr = tp2_rr
        self.enable_friday_close = enable_friday_close
        self.friday_close_hour_utc = friday_close_hour_utc
        self.enable_session_filter = enable_session_filter
        self.session_start_hour_utc = session_start_hour_utc
        self.session_end_hour_utc = session_end_hour_utc
        self.max_stop_loss_pips = max_stop_loss_pips
        self.risk_engine = risk_engine or RiskEngine(
            default_lot_size=0.05,
            min_lot_size=0.05,
            max_open_trades=10,
            max_trades_per_symbol=2,
        )
        self.entry_engine = entry_engine or EntryEngine(
            allow_ranging_trend=True,
            enable_session_filter=enable_session_filter,
            session_start_hour_utc=session_start_hour_utc,
            session_end_hour_utc=session_end_hour_utc,
            require_rejection_confirmation=True,
            require_expansion=False,
            require_htf_alignment=True,
            require_trend_alignment=True,
            min_penetration_ticks=0,
            require_stay_beyond=False,
            max_stop_loss_pips=max_stop_loss_pips,
        )
        self.exit_engine = exit_engine or ExitEngine(
            risk_reward_ratio=3.0,
            take_profit_pips=None,
            early_breakeven_trigger_pips=self.breakeven_pips,
            early_breakeven_buffer_pips=self.breakeven_buffer_pips,
        )
        self.analysis_engine = AnalysisEngine(
            sweep_detector=SweepDetector(
                min_penetration_ticks=0,
                min_hold_candles=0,
                min_hold_seconds=0.0,
                min_penetration_pips_floor=getattr(settings, "min_penetration_pips_floor", 0.8) if settings else 0.8,
            )
        )
        self.poll_interval_seconds = poll_interval_seconds

        self.executor = MT5Executor()
        self.tracked_zones: dict[str, list[LiquidityZone]] = {}
        self.executed_setup_keys: set[str] = set()
        self._is_running = False

    def get_tracked_zones(self, symbol: str, timeframe_str: str) -> list[LiquidityZone]:
        key = f"{symbol.upper()}:{timeframe_str.lower()}"
        return self.tracked_zones.get(key, [])

    def set_tracked_zones(self, symbol: str, timeframe_str: str, zones: list[LiquidityZone]) -> None:
        key = f"{symbol.upper()}:{timeframe_str.lower()}"
        self.tracked_zones[key] = zones

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
            db.rollback()
            db.close()

        # 4b. Check Friday End-of-Week Protection (Close before weekend spread widening)
        now_utc = datetime.now(timezone.utc)
        is_friday_evening = (now_utc.weekday() == 4 and now_utc.hour >= self.friday_close_hour_utc) or (now_utc.weekday() == 5)
        if self.enable_friday_close and is_friday_evening:
            if open_positions:
                logger.warning(
                    f"[TradingRunner] Friday market close safeguard active ({now_utc.strftime('%A %H:%M UTC')}). "
                    f"Closing {len(open_positions)} open positions to eliminate weekend risk..."
                )
                self.close_all_positions(open_positions)
            return

        # Check max open trades
        if len(open_positions) >= self.risk_engine.max_open_trades:
            logger.debug(f"[TradingRunner] Max open trades ({self.risk_engine.max_open_trades}) reached. Skipping new entries.")
            scan_for_entries = False
        else:
            scan_for_entries = True

        # Heartbeat log every ~60s (every 6 cycles at 10s poll interval)
        self._cycle_count = getattr(self, "_cycle_count", 0) + 1
        if self._cycle_count % 6 == 1:
            logger.info(
                f"[TradingRunner] Active: scanning {len(self.watchlist)} symbols | "
                f"Open MT5 positions: {len(open_positions)} | "
                f"Balance: ${account_dict.get('balance', 0.0):.2f} | "
                f"Free Margin: ${account_dict.get('margin_free', 0.0):.2f}"
            )

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

    def close_all_positions(self, positions: list, is_friday_close: bool = True) -> None:
        """Closes all open positions before weekend or high-risk market periods."""
        for p in positions:
            ticket = int(p.get("ticket", 0))
            symbol = str(p.get("symbol", ""))
            vol = float(p.get("volume", 0.0))
            order_type = "BUY" if int(p.get("type", 0)) == 0 else "SELL"
            try:
                res = self.executor.close_position(ticket=ticket, symbol=symbol, volume=vol, order_type=order_type)
                if res.get("success"):
                    logger.success(f"[TradingRunner] Closed position {ticket} ({symbol}) for weekend safeguard.")
            except Exception as e:
                logger.error(f"[TradingRunner] Error closing position {ticket}: {e}")
        self.sync_positions(is_friday_close=is_friday_close)

    def sync_positions(self, is_friday_close: bool = False) -> None:
        """Syncs open positions in MT5 against DB records, detecting closures, realized PnL, and managing Break-Even."""
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
                    current_p = pos.get("price_current", trade.close_price)
                    trade.close_price = current_p

                    # Early Break-Even Protection Check
                    if self.breakeven_pips > 0 and trade.open_price:
                        is_buy = (trade.order_type or "").upper() == "BUY"
                        entry_p = float(trade.open_price)
                        pip_size = 0.01 if "JPY" in trade.symbol.upper() else 0.0001
                        should_be = self.exit_engine.should_trigger_breakeven(
                            direction=trade.order_type,
                            entry_price=entry_p,
                            current_price=current_p,
                            pip_size=pip_size,
                            trigger_pips=self.breakeven_pips,
                        )
                        if should_be:
                            be_price = self.exit_engine.compute_breakeven_sl(
                                direction=trade.order_type,
                                entry_price=entry_p,
                                pip_size=pip_size,
                                buffer_pips=self.breakeven_buffer_pips,
                            )
                            current_sl = float(pos.get("sl") or trade.stop_loss or 0.0)
                            current_tp = float(pos.get("tp") or trade.take_profit or 0.0)

                            sl_needs_update = False
                            if is_buy:
                                if current_sl < be_price:
                                    sl_needs_update = True
                            else:
                                if current_sl <= 0.0 or current_sl > be_price:
                                    sl_needs_update = True

                            if sl_needs_update:
                                pips_in_profit = (current_p - entry_p) / pip_size if is_buy else (entry_p - current_p) / pip_size
                                logger.info(
                                    f"[TradingRunner] Position {trade.ticket} ({trade.symbol}) reached +{pips_in_profit:.1f} pips profit. "
                                    f"Moving Stop Loss to Break-Even ({be_price:.5f})."
                                )
                                mod_res = self.executor.modify_position(
                                    ticket=trade.ticket,
                                    symbol=trade.symbol,
                                    stop_loss=be_price,
                                    take_profit=current_tp,
                                )
                                if mod_res.get("success"):
                                    trade.stop_loss = be_price
                                    logger.success(f"[TradingRunner] Position {trade.ticket} protected at Break-Even ({be_price:.5f})!")
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

                    # Classify and record exit_type on TradeModel
                    close_p = trade.close_price if trade.close_price is not None else trade.open_price
                    pip_size = 0.01 if "JPY" in trade.symbol.upper() else 0.0001
                    deal_comment = (exit_deal.get("comment") if exit_deal else "") or ""
                    tp_label = "TP2" if "P2" in deal_comment else ("TP1" if "P1" in deal_comment else None)

                    exit_type = self.exit_engine.determine_exit_type(
                        direction=trade.order_type,
                        entry_price=trade.open_price,
                        exit_price=close_p,
                        stop_loss=trade.stop_loss,
                        take_profit=trade.take_profit,
                        is_friday_close=is_friday_close,
                        tp_label=tp_label,
                        pip_size=pip_size,
                    )
                    trade.exit_type = exit_type.value
                    logger.success(
                        f"[TradingRunner] Position {trade.ticket} ({trade.symbol}) closed [{trade.exit_type}]. Final profit: ${trade.profit:.2f}"
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
        """Fetches M15 and H1 candles, performs multi-timeframe analysis, persists to DB, and executes qualifying signals."""
        m15_tf_str = self.timeframe.value if hasattr(self.timeframe, "value") else str(self.timeframe).lower()
        h1_tf_str = self.htf_timeframe.value if hasattr(self.htf_timeframe, "value") else str(self.htf_timeframe).lower()

        # 1. Fetch candles for both M15 and H1
        candles_m15 = self.executor.fetch_candles(symbol, self.timeframe, self.candle_count)
        candles_h1 = self.executor.fetch_candles(symbol, self.htf_timeframe, self.candle_count)

        if not candles_m15 or len(candles_m15) < 30:
            return

        # 2. Run Analysis for H1 (Higher Timeframe)
        snapshot_h1 = None
        if candles_h1 and len(candles_h1) >= 20:
            existing_h1 = self.get_tracked_zones(symbol, h1_tf_str)
            snapshot_h1 = self.analysis_engine.analyze(candles_h1, existing_zones=existing_h1)
            self.set_tracked_zones(symbol, h1_tf_str, snapshot_h1.zones)
            self._persist_analysis(symbol, candles_h1, snapshot_h1, timeframe_str=h1_tf_str)

        # 3. Run Analysis for M15 (Primary / Execution Timeframe)
        existing_m15 = self.get_tracked_zones(symbol, m15_tf_str)
        snapshot_m15 = self.analysis_engine.analyze(candles_m15, existing_zones=existing_m15)
        self.set_tracked_zones(symbol, m15_tf_str, snapshot_m15.zones)
        self._persist_analysis(symbol, candles_m15, snapshot_m15, timeframe_str=m15_tf_str)

        # 4. Check if we should evaluate and open trades
        if not scan_for_entries or symbol.upper() in open_symbols:
            return

        # Session / Killzone Filter: Avoid Asian and rollover low-volume dead zones (21:00 - 06:45 UTC)
        if self.enable_session_filter:
            now_utc = datetime.now(timezone.utc)
            if now_utc.hour < self.session_start_hour_utc or now_utc.hour >= self.session_end_hour_utc:
                return

        # 5. Generate entry signals with Multi-Timeframe Confluence (live structure classification against H1)
        req_htf = (
            (self.entry_engine.require_htf_alignment and symbol.upper() in self.htf_alignment_symbols)
            if self.htf_alignment_symbols is not None
            else None
        )
        signals = self.entry_engine.evaluate(
            snapshot=snapshot_m15,
            candles=candles_m15,
            htf_snapshot=snapshot_h1,
            htf_candles=candles_h1 if candles_h1 else None,
            require_htf_alignment=req_htf,
        )

        # Also evaluate direct H1 sweep setups if no M15 signal
        if not signals and snapshot_h1 and candles_h1 and len(candles_h1) >= 30:
            h1_signals = self.entry_engine.evaluate(
                snapshot=snapshot_h1,
                candles=candles_h1,
                require_htf_alignment=req_htf,
            )
            if h1_signals:
                signals.extend(h1_signals)

        if not signals:
            return

        # 6. Find qualifying signal
        for signal in signals:
            signal_candles = candles_h1 if (signal.timeframe == self.htf_timeframe and candles_h1) else candles_m15
            signal_candle_idx = None
            for idx, c in enumerate(signal_candles):
                if c.timestamp == signal.signal_time:
                    signal_candle_idx = idx
                    break

            if signal_candle_idx is not None:
                candle_age = len(signal_candles) - 1 - signal_candle_idx
                if candle_age > self.max_signal_age_candles:
                    continue  # Stale setup

            sig_tf_str = signal.timeframe.value if hasattr(signal.timeframe, "value") else str(signal.timeframe)
            setup_key = f"{signal.symbol}_{sig_tf_str}_{signal.zone_id}_{signal.signal_time.isoformat()}"
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

            # 7. Risk Check (refresh real-time free margin)
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
                logger.info(f"[TradingRunner] Signal for {signal.symbol} ({sig_tf_str}) rejected by risk engine: {risk_res.reason}")
                continue

            # 8. Execute live orders on MT5 (Split targets: P1 = conservative TP1, P2 = runner TP2)
            opened_any = False
            for pos_num in range(1, self.positions_per_trade + 1):
                target_rr = self.tp1_rr if pos_num == 1 else self.tp2_rr
                pos_exits = self.exit_engine.compute_exit_levels(signal, custom_rr=target_rr)

                # Validate price against position-specific exits
                if signal.direction == TradeDirection.BUY:
                    if current_price <= pos_exits.stop_loss or current_price >= pos_exits.take_profit:
                        continue
                else:
                    if current_price >= pos_exits.stop_loss or current_price <= pos_exits.take_profit:
                        continue

                try:
                    acc_check = self.executor.get_account_info()
                    if acc_check is not None:
                        free_val = getattr(acc_check, "margin_free", None)
                        if free_val is not None and isinstance(free_val, (int, float)) and free_val < 2.0:
                            logger.warning(f"[TradingRunner] Insufficient free margin for position {pos_num}/{self.positions_per_trade}. Skipping.")
                            break
                except Exception:
                    pass

                comment_tag = f"LiquidityBot P{pos_num}-R{target_rr:.1f}"
                logger.info(
                    f"[TradingRunner] Executing {signal.direction.value.upper()} position {pos_num}/{self.positions_per_trade} "
                    f"on {signal.symbol} [{sig_tf_str}] ({risk_res.lot_size} lots) | SL={pos_exits.stop_loss:.5f} | TP={pos_exits.take_profit:.5f} (RR: {target_rr})"
                )
                order_res = self.executor.open_order(
                    symbol=signal.symbol,
                    order_type=signal.direction.value,
                    volume=risk_res.lot_size,
                    stop_loss=pos_exits.stop_loss,
                    take_profit=pos_exits.take_profit,
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
                            stop_loss=pos_exits.stop_loss,
                            take_profit=pos_exits.take_profit,
                            profit=0.0,
                            status="OPEN",
                            timeframe=sig_tf_str,
                            opened_at=datetime.now(timezone.utc),
                        )
                        db.add(new_trade)
                        db.commit()
                        logger.success(
                            f"[TradingRunner] Opened position {pos_num}/{self.positions_per_trade} "
                            f"(Ticket #{ticket}) on {signal.symbol} [{sig_tf_str}] ({risk_res.lot_size} lots)!"
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
                break  # Setup executed with 2 positions

    def _persist_analysis(
        self,
        symbol: str,
        candles: list[Candle],
        snapshot: MarketSnapshot,
        timeframe_str: str = "15m",
    ) -> None:
        """Persists detected liquidity zones, sweeps, and market snapshot into PostgreSQL."""
        db: Session = SessionLocal()
        try:
            # 1. Persist/update Liquidity Zones
            for z in snapshot.zones:
                existing_zone = (
                    db.query(LiquidityZoneModel)
                    .filter_by(
                        symbol=symbol.upper(),
                        timeframe=timeframe_str,
                        side=z.side.value,
                        created_at=z.created_at,
                    )
                    .first()
                )
                if existing_zone:
                    existing_zone.status = z.status.value
                    existing_zone.touches = z.touches
                    existing_zone.swept_at = z.swept_at
                    existing_zone.sweep_price = z.sweep_price
                else:
                    db_zone = LiquidityZoneModel(
                        id=z.id,
                        symbol=symbol.upper(),
                        timeframe=timeframe_str,
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
                        timeframe=timeframe_str,
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
                .filter_by(symbol=symbol.upper(), timeframe=timeframe_str)
                .order_by(MarketSnapshotModel.recorded_at.desc())
                .first()
            )

            now_utc = datetime.now(timezone.utc)
            if not latest_snap or (now_utc - latest_snap.recorded_at).total_seconds() >= 300:
                snap_rec = MarketSnapshotModel(
                    symbol=symbol.upper(),
                    timeframe=timeframe_str,
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
