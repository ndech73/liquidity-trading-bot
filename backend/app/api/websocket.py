import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from sqlalchemy.orm import Session

from app.core.settings import PRODUCTION_WATCHLIST
from app.db.session import SessionLocal
from app.db.models.trade import TradeModel
from app.execution.mt5_executor import MT5Executor

router = APIRouter()

WATCHLIST = PRODUCTION_WATCHLIST


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"[WebSocket] Client connected. Total active connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"[WebSocket] Client disconnected. Remaining: {len(self.active_connections)}")

    def count(self) -> int:
        return len(self.active_connections)

    async def broadcast(self, channel: str, message_type: str, data: Any):
        if not self.active_connections:
            return

        payload = {
            "channel": channel,
            "type": message_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        async with self._lock:
            connections = list(self.active_connections)

        dead_connections = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception:
                dead_connections.append(connection)

        if dead_connections:
            async with self._lock:
                for dead in dead_connections:
                    self.active_connections.discard(dead)


manager = ConnectionManager()


def gather_live_state() -> Dict[str, Any]:
    """Synchronous function to gather MT5 quotes, account, and open trades.
    Executed via asyncio.to_thread to avoid blocking the event loop."""
    account_data = {
        "login": None,
        "balance": 0.0,
        "equity": 0.0,
        "currency": "USD",
        "connected": False,
        "status": "OFFLINE",
        "open_trades_count": 0,
        "unrealized_pnl": 0.0,
    }

    quotes = []
    trades = []

    # 1. Fetch from DB if available
    db: Session = SessionLocal()
    try:
        open_db_trades = db.query(TradeModel).filter_by(status="OPEN").all()
        account_data["open_trades_count"] = len(open_db_trades)
        account_data["unrealized_pnl"] = round(sum(t.profit for t in open_db_trades), 2)
        for t in open_db_trades:
            trades.append({
                "id": f"t-{t.ticket}",
                "ticket": t.ticket,
                "symbol": t.symbol,
                "type": t.order_type,
                "orderType": t.order_type,
                "lots": t.lots,
                "openPrice": t.open_price,
                "currentPrice": t.close_price or t.open_price,
                "stopLoss": t.stop_loss,
                "takeProfit": t.take_profit,
                "profit": t.profit,
                "openTime": t.opened_at.isoformat(),
                "duration": "Active",
            })
    except Exception as e:
        logger.debug(f"[WebSocket] Error querying DB trades: {e}")
    finally:
        db.rollback()
        db.close()

    # 2. Query MT5 if bridge is active
    executor = None
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

            # Fetch live quotes for watchlist
            if executor.mt5:
                for symbol in WATCHLIST:
                    bid, ask, spread_pips = 0.0, 0.0, 0.0
                    try:
                        tick = executor.mt5.symbol_info_tick(symbol)
                        if tick:
                            bid = float(tick.bid)
                            ask = float(tick.ask)
                            sym_info = executor.mt5.symbol_info(symbol)
                            point = sym_info.point if sym_info else 0.0001
                            spread_pips = round((ask - bid) / (point * 10), 1)
                    except Exception:
                        pass
                    quotes.append({
                        "symbol": symbol,
                        "bid": bid,
                        "ask": ask,
                        "spreadPips": spread_pips,
                        "change24h": 0.0,
                        "status": "LIVE" if bid > 0 else "OFFLINE",
                    })

                # Fetch live positions from MT5 if available
                positions = executor.get_positions()
                if positions:
                    trades = []
                    for p in positions:
                        p_type = "BUY" if p.get("type") == 0 else "SELL"
                        trades.append({
                            "id": f"mt5-{p.get('ticket')}",
                            "ticket": p.get("ticket"),
                            "symbol": p.get("symbol"),
                            "type": p_type,
                            "orderType": p_type,
                            "lots": p.get("volume", 0.01),
                            "openPrice": p.get("price_open", 0.0),
                            "currentPrice": p.get("price_current", 0.0),
                            "stopLoss": p.get("sl", 0.0),
                            "takeProfit": p.get("tp", 0.0),
                            "profit": round(p.get("profit", 0.0), 2),
                            "openTime": datetime.now(timezone.utc).isoformat(),
                            "duration": "Active",
                        })
                    account_data["open_trades_count"] = len(trades)
                    account_data["unrealized_pnl"] = round(sum(t["profit"] for t in trades), 2)
    except Exception as e:
        logger.debug(f"[WebSocket] Error during MT5 live query: {e}")
    finally:
        if executor:
            try:
                executor.close()
            except Exception:
                pass

    if not quotes:
        for symbol in WATCHLIST:
            quotes.append({
                "symbol": symbol,
                "bid": 0.0,
                "ask": 0.0,
                "spreadPips": 0.0,
                "change24h": 0.0,
                "status": "OFFLINE",
            })

    return {
        "account": account_data,
        "markets": quotes,
        "trades": trades,
    }


async def ws_relay_worker():
    """Background loop that relays live data to connected WebSocket clients."""
    logger.info("[WebSocket] Relay worker loop started.")
    try:
        while True:
            if manager.count() > 0:
                try:
                    state = await asyncio.to_thread(gather_live_state)
                    await manager.broadcast("markets", "quotes", state["markets"])
                    await manager.broadcast("account", "update", state["account"])
                    await manager.broadcast("trades", "update", state["trades"])
                    await manager.broadcast("system", "heartbeat", {
                        "clients": manager.count(),
                        "server_time": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as e:
                    logger.warning(f"[WebSocket] Error in relay broadcast: {e}")
                await asyncio.sleep(2.0)
            else:
                await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        logger.info("[WebSocket] Relay worker loop stopped.")


@router.websocket("/ws")
@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    # Initial handshake
    await websocket.send_json({
        "channel": "system",
        "type": "connected",
        "data": {
            "status": "online",
            "server_time": datetime.now(timezone.utc).isoformat(),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Immediate initial state relay
    try:
        initial_state = await asyncio.to_thread(gather_live_state)
        await websocket.send_json({
            "channel": "account",
            "type": "update",
            "data": initial_state["account"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await websocket.send_json({
            "channel": "markets",
            "type": "quotes",
            "data": initial_state["markets"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        await websocket.send_json({
            "channel": "trades",
            "type": "update",
            "data": initial_state["trades"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"[WebSocket] Error sending initial state: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                msg = {"action": data}

            action = msg.get("action") or msg.get("type")
            if action == "ping":
                await websocket.send_json({
                    "channel": "system",
                    "type": "pong",
                    "data": {"server_time": datetime.now(timezone.utc).isoformat()},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            elif action == "sync":
                state = await asyncio.to_thread(gather_live_state)
                await websocket.send_json({
                    "channel": "account",
                    "type": "update",
                    "data": state["account"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                await websocket.send_json({
                    "channel": "markets",
                    "type": "quotes",
                    "data": state["markets"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                await websocket.send_json({
                    "channel": "trades",
                    "type": "update",
                    "data": state["trades"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"[WebSocket] Client error: {e}")
        await manager.disconnect(websocket)

