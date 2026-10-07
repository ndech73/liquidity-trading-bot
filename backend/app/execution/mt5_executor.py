import os
import threading
from datetime import datetime
from typing import Optional
from loguru import logger


class MT5Executor:
    """Thin execution adapter supporting both native Windows MT5 and Linux Wine bridge."""

    _lock = threading.Lock()
    _shared_conn = None
    _shared_mt5 = None

    def __init__(self, host: str = "127.0.0.1", port: int = 18812):
        self.host = host
        self.port = port
        self.mt5 = MT5Executor._shared_mt5
        self._conn = MT5Executor._shared_conn

    def connect(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
    ) -> bool:
        """Connects to MT5 terminal, reusing persistent shared session to eliminate RPC latency."""
        with MT5Executor._lock:
            # 1. Fast-path: Check if existing shared connection is alive and authorized
            if MT5Executor._shared_mt5 is not None:
                try:
                    terminal = MT5Executor._shared_mt5.terminal_info()
                    if terminal and getattr(terminal, "connected", False):
                        self.mt5 = MT5Executor._shared_mt5
                        self._conn = MT5Executor._shared_conn
                        return True
                except Exception:
                    MT5Executor._shared_mt5 = None
                    MT5Executor._shared_conn = None

            # 2. Attempt native MetaTrader5 (Windows)
            try:
                import MetaTrader5 as native_mt5
                self.mt5 = native_mt5
                MT5Executor._shared_mt5 = native_mt5
                logger.info("Using native Windows MetaTrader5 package.")
            except ImportError:
                # 3. Fall back to Wine RPC bridge (mt5server.exe / rpyc)
                try:
                    import rpyc
                    logger.info(f"Connecting to Wine MT5 RPC server at {self.host}:{self.port}...")
                    self._conn = rpyc.classic.connect(self.host, self.port)
                    self._conn._config["sync_request_timeout"] = 60
                    self.mt5 = self._conn.modules.MetaTrader5
                    MT5Executor._shared_conn = self._conn
                    MT5Executor._shared_mt5 = self.mt5
                    logger.success("Connected to Wine MT5 bridge.")
                except Exception as e:
                    logger.error(f"Failed to connect to MT5 Wine bridge: {e}")
                    raise RuntimeError(
                        f"Could not connect to MT5 Wine bridge at {self.host}:{self.port}. "
                        "Ensure 'wine ~/.mt5/mt5server.exe' or 'scripts/start_mt5_bridge.sh' is running."
                    ) from e

            # Initialize MT5 session
            login = login or (int(os.getenv("MT5_LOGIN")) if os.getenv("MT5_LOGIN") else None)
            password = password or os.getenv("MT5_PASSWORD")
            server = server or os.getenv("MT5_SERVER")
            terminal_path = os.getenv("MT5_TERMINAL_PATH")
            clean_path = None
            if terminal_path and terminal_path.strip():
                raw_path = terminal_path.strip().strip('"\'')
                mt5_prefix_c = os.path.expanduser("~/.mt5/drive_c")
                if raw_path.startswith(mt5_prefix_c):
                    clean_path = "C:" + raw_path[len(mt5_prefix_c):].replace("/", "\\")
                elif raw_path.startswith("/"):
                    clean_path = "Z:" + raw_path.replace("/", "\\")
                else:
                    clean_path = raw_path

            # Initialize terminal connection with credentials directly to avoid modal account dialogs
            success = False
            int_login = int(login) if login else None
            try:
                if int_login and password and server:
                    if clean_path:
                        try:
                            success = self.mt5.initialize(path=clean_path, login=int_login, password=password, server=server, timeout=15000)
                        except Exception:
                            success = False
                    if not success:
                        success = self.mt5.initialize(login=int_login, password=password, server=server, timeout=15000)
                else:
                    success = self.mt5.initialize()
                    if not success and clean_path:
                        success = self.mt5.initialize(path=clean_path)
            except Exception as e:
                logger.warning(f"Error initializing MT5: {e}")
                success = False

            if not success:
                # Try fallback basic initialize
                try:
                    success = self.mt5.initialize()
                except Exception:
                    pass

            if not success:
                last_err = self.mt5.last_error()
                logger.error(f"MT5 initialization failed: {last_err}")
                return False

            # Verify authorization
            if int_login and password and server:
                try:
                    curr_info = self.mt5.account_info()
                    if not curr_info or getattr(curr_info, "login", None) != int_login:
                        login_success = self.mt5.login(int_login, password=password, server=server)
                        if not login_success:
                            last_err = self.mt5.last_error()
                            logger.warning(
                                f"MT5 login failed for account {login} on {server}: {last_err}. "
                                "Check demo credentials in .env or MT5 terminal."
                            )
                            return False
                        logger.success(f"MT5 authorized on account {login} ({server}).")
                except Exception as e:
                    logger.warning(f"Error checking MT5 account status: {e}")

            terminal = self.mt5.terminal_info()
            logger.success(
                f"MT5 session active: {getattr(terminal, 'name', 'Terminal')} (connected: {getattr(terminal, 'connected', False)})"
            )
            return True

    def get_account_info(self):
        """Fetch live account details."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")
        with MT5Executor._lock:
            return self.mt5.account_info()

    def get_terminal_info(self):
        """Fetch terminal state details."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")
        with MT5Executor._lock:
            return self.mt5.terminal_info()

    def _map_timeframe(self, tf):
        tf_str = str(tf.value if hasattr(tf, "value") else tf).lower()
        mapping = {
            "1m": getattr(self.mt5, "TIMEFRAME_M1", 1),
            "5m": getattr(self.mt5, "TIMEFRAME_M5", 5),
            "15m": getattr(self.mt5, "TIMEFRAME_M15", 15),
            "30m": getattr(self.mt5, "TIMEFRAME_M30", 30),
            "1h": getattr(self.mt5, "TIMEFRAME_H1", 16385),
            "4h": getattr(self.mt5, "TIMEFRAME_H4", 16388),
            "1d": getattr(self.mt5, "TIMEFRAME_D1", 16408),
            "1w": getattr(self.mt5, "TIMEFRAME_W1", 32769),
            "1mn": getattr(self.mt5, "TIMEFRAME_MN1", 49153),
            "m1": getattr(self.mt5, "TIMEFRAME_M1", 1),
            "m5": getattr(self.mt5, "TIMEFRAME_M5", 5),
            "m15": getattr(self.mt5, "TIMEFRAME_M15", 15),
            "m30": getattr(self.mt5, "TIMEFRAME_M30", 30),
            "h1": getattr(self.mt5, "TIMEFRAME_H1", 16385),
            "h4": getattr(self.mt5, "TIMEFRAME_H4", 16388),
            "d1": getattr(self.mt5, "TIMEFRAME_D1", 16408),
            "w1": getattr(self.mt5, "TIMEFRAME_W1", 32769),
            "mn": getattr(self.mt5, "TIMEFRAME_MN1", 49153),
            "mn1": getattr(self.mt5, "TIMEFRAME_MN1", 49153),
        }
        return mapping.get(tf_str, getattr(self.mt5, "TIMEFRAME_M5", 5))

    def fetch_candles(self, symbol: str, timeframe, count: int = 200):
        """Fetches candles from MT5 and transforms them to domain Candle objects."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")
        from datetime import datetime, timezone
        from app.analysis_engine.domain.candle import Candle, Timeframe as DomainTF

        tf_const = self._map_timeframe(timeframe)
        with MT5Executor._lock:
            rates = self.mt5.copy_rates_from_pos(symbol, tf_const, 0, count)
            if rates is None or len(rates) == 0:
                return []
            try:
                import rpyc
                raw_list = rpyc.classic.obtain(rates.tolist())
            except Exception:
                raw_list = [
                    (
                        int(r["time"]),
                        float(r["open"]),
                        float(r["high"]),
                        float(r["low"]),
                        float(r["close"]),
                        float(r["tick_volume"]) if "tick_volume" in r.dtype.names else None,
                    )
                    for r in rates
                ]

        domain_str = str(timeframe.value if hasattr(timeframe, "value") else timeframe).lower()
        domain_norm = {
            "m1": "1m", "m5": "5m", "m15": "15m", "m30": "30m",
            "h1": "1h", "h4": "4h", "d1": "1d", "w1": "1w", "mn": "1mn", "mn1": "1mn"
        }.get(domain_str, domain_str)

        try:
            domain_tf = DomainTF(domain_norm)
        except ValueError:
            domain_tf = DomainTF.M5

        candles = []
        for item in raw_list:
            t_val, o_val, h_val, l_val, c_val = item[0], item[1], item[2], item[3], item[4]
            vol_val = float(item[5]) if len(item) > 5 and item[5] is not None else None
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=domain_tf,
                    timestamp=datetime.fromtimestamp(int(t_val), tz=timezone.utc),
                    open=float(o_val),
                    high=float(h_val),
                    low=float(l_val),
                    close=float(c_val),
                    volume=vol_val,
                )
            )
        return candles

    def fetch_candles_range(self, symbol: str, timeframe, date_from: datetime, date_to: datetime):
        """Fetches historical candles within a specific date range from MT5."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")
        from datetime import timezone
        from app.analysis_engine.domain.candle import Candle, Timeframe as DomainTF

        tf_const = self._map_timeframe(timeframe)
        with MT5Executor._lock:
            remote_code = f"""
import MetaTrader5 as mt5
from datetime import datetime
_rates = mt5.copy_rates_range('{symbol}', {tf_const}, datetime.fromtimestamp({int(date_from.timestamp())}), datetime.fromtimestamp({int(date_to.timestamp())}))
"""
            try:
                self._conn.execute(remote_code)
                rates = self._conn.namespace.get("_rates")
            except Exception:
                rates = self.mt5.copy_rates_range(symbol, tf_const, date_from, date_to)

            if rates is None or len(rates) == 0:
                return []
            try:
                import rpyc
                raw_list = rpyc.classic.obtain(rates.tolist())
            except Exception:
                raw_list = [
                    (
                        int(r["time"]),
                        float(r["open"]),
                        float(r["high"]),
                        float(r["low"]),
                        float(r["close"]),
                        float(r["tick_volume"]) if "tick_volume" in r.dtype.names else None,
                    )
                    for r in rates
                ]

        domain_str = str(timeframe.value if hasattr(timeframe, "value") else timeframe).lower()
        domain_norm = {
            "m1": "1m", "m5": "5m", "m15": "15m", "m30": "30m",
            "h1": "1h", "h4": "4h", "d1": "1d", "w1": "1w", "mn": "1mn", "mn1": "1mn"
        }.get(domain_str, domain_str)

        try:
            domain_tf = DomainTF(domain_norm)
        except ValueError:
            domain_tf = DomainTF.M15

        candles = []
        for item in raw_list:
            t_val, o_val, h_val, l_val, c_val = item[0], item[1], item[2], item[3], item[4]
            vol_val = float(item[5]) if len(item) > 5 and item[5] is not None else None
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=domain_tf,
                    timestamp=datetime.fromtimestamp(int(t_val), tz=timezone.utc),
                    open=float(o_val),
                    high=float(h_val),
                    low=float(l_val),
                    close=float(c_val),
                    volume=vol_val,
                )
            )
        return candles

    def get_positions(self, symbol: Optional[str] = None):
        """Fetch open positions from MT5, normalized as python dicts."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")
        with MT5Executor._lock:
            try:
                raw_pos = self.mt5.positions_get(symbol=symbol) if symbol else self.mt5.positions_get()
                if not raw_pos:
                    return []
                res = []
                for p in raw_pos:
                    res.append({
                        "ticket": int(getattr(p, "ticket", 0)),
                        "symbol": str(getattr(p, "symbol", "")),
                        "type": int(getattr(p, "type", 0)),
                        "volume": float(getattr(p, "volume", 0.0)),
                        "price_open": float(getattr(p, "price_open", 0.0)),
                        "price_current": float(getattr(p, "price_current", 0.0)),
                        "sl": float(getattr(p, "sl", 0.0)),
                        "tp": float(getattr(p, "tp", 0.0)),
                        "profit": float(getattr(p, "profit", 0.0)),
                        "time": int(getattr(p, "time", 0)),
                    })
                return res
            except Exception as e:
                logger.warning(f"Error fetching positions from MT5: {e}")
                return []

    def get_position_deals(self, position_id: int):
        """Fetch historical deals for a position to retrieve exit price and realized profit."""
        if not self.mt5:
            return []
        with MT5Executor._lock:
            try:
                raw_deals = self.mt5.history_deals_get(position=int(position_id))
                if not raw_deals:
                    return []
                res = []
                for d in raw_deals:
                    res.append({
                        "ticket": int(getattr(d, "ticket", 0)),
                        "order": int(getattr(d, "order", 0)),
                        "time": int(getattr(d, "time", 0)),
                        "type": int(getattr(d, "type", 0)),
                        "entry": int(getattr(d, "entry", 0)),
                        "position_id": int(getattr(d, "position_id", 0)),
                        "volume": float(getattr(d, "volume", 0.0)),
                        "price": float(getattr(d, "price", 0.0)),
                        "profit": float(getattr(d, "profit", 0.0)),
                        "symbol": str(getattr(d, "symbol", "")),
                        "commission": float(getattr(d, "commission", 0.0)),
                        "swap": float(getattr(d, "swap", 0.0)),
                    })
                return res
            except Exception as e:
                logger.warning(f"Error fetching deals for position {position_id}: {e}")
                return []


    def ensure_algo_trading(self) -> bool:
        """Verifies that Algo Trading is enabled in MT5. If not, toggles it on."""
        if not self.mt5:
            return False
        with MT5Executor._lock:
            try:
                t = self.mt5.terminal_info()
                if t and getattr(t, "trade_allowed", False):
                    return True
                if self._conn:
                    user32 = self._conn.modules.ctypes.windll.user32
                    WNDENUMPROC = self._conn.modules.ctypes.WINFUNCTYPE(
                        self._conn.modules.ctypes.c_bool,
                        self._conn.modules.ctypes.c_void_p,
                        self._conn.modules.ctypes.c_void_p,
                    )
                    mt5_hwnds = []

                    def enum_cb(hwnd, lparam):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = self._conn.modules.ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buff, length + 1)
                            if "MetaTrader" in buff.value or "FBS" in buff.value:
                                mt5_hwnds.append(hwnd)
                        return True

                    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
                    for h in mt5_hwnds:
                        user32.PostMessageA(h, 0x0111, 32851, 0)
                    logger.info("Sent Algo Trading toggle command (32851) to MT5.")
                    return True
            except Exception as e:
                logger.warning(f"Could not auto-toggle Algo Trading: {e}")
        return False

    def open_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        comment: str = "LiquidityBot",
    ) -> dict:
        """Executes a live market order on MT5. order_type is 'buy' or 'sell'."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")

        self.ensure_algo_trading()

        with MT5Executor._lock:
            sym_info = self.mt5.symbol_info(symbol)
            if not sym_info:
                return {"success": False, "error": f"Symbol {symbol} not found"}
            if not getattr(sym_info, "visible", True):
                self.mt5.symbol_select(symbol, True)

            tick = self.mt5.symbol_info_tick(symbol)
            if not tick:
                return {"success": False, "error": f"Could not get tick for {symbol}"}

            is_buy = order_type.lower() == "buy"
            mql_type = getattr(self.mt5, "ORDER_TYPE_BUY", 0) if is_buy else getattr(self.mt5, "ORDER_TYPE_SELL", 1)
            price = float(tick.ask if is_buy else tick.bid)

            digits = int(getattr(sym_info, "digits", 5))
            sl = round(float(stop_loss), digits) if stop_loss > 0 else 0.0
            tp = round(float(take_profit), digits) if take_profit > 0 else 0.0
            vol = round(float(volume), 2)

            filling_mode = getattr(sym_info, "filling_mode", 0)
            if filling_mode & 2:
                filling_type = getattr(self.mt5, "ORDER_FILLING_IOC", 1)
            elif filling_mode & 1:
                filling_type = getattr(self.mt5, "ORDER_FILLING_FOK", 0)
            else:
                filling_type = getattr(self.mt5, "ORDER_FILLING_RETURN", 2)

            remote_code = f"""
import MetaTrader5 as mt5
_res = mt5.order_send({{
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': '{symbol}',
    'volume': {vol},
    'type': {mql_type},
    'price': {price},
    'sl': {sl},
    'tp': {tp},
    'deviation': 20,
    'magic': 100888,
    'comment': '{comment}',
    'type_time': mt5.ORDER_TIME_GTC,
    'type_filling': {filling_type},
}})
"""
            try:
                self._conn.execute(remote_code)
                res = self._conn.namespace.get("_res")
            except Exception:
                req = {
                    "action": getattr(self.mt5, "TRADE_ACTION_DEAL", 1),
                    "symbol": symbol,
                    "volume": vol,
                    "type": mql_type,
                    "price": price,
                    "sl": sl,
                    "tp": tp,
                    "deviation": 20,
                    "magic": 100888,
                    "comment": comment,
                    "type_time": getattr(self.mt5, "ORDER_TIME_GTC", 0),
                    "type_filling": filling_type,
                }
                res = self.mt5.order_send(req)

            if res and getattr(res, "retcode", 0) in [10008, 10009]:
                logger.success(
                    f"Order executed: {symbol} {order_type.upper()} {vol} lots @ {res.price} (Ticket: {res.order})"
                )
                return {
                    "success": True,
                    "ticket": res.order,
                    "deal": res.deal,
                    "price": res.price,
                    "volume": res.volume,
                    "retcode": res.retcode,
                    "comment": res.comment,
                }
            else:
                retcode = getattr(res, "retcode", -1) if res else -1
                comment_msg = getattr(res, "comment", "Unknown error") if res else str(self.mt5.last_error())
                logger.error(f"Order failed for {symbol} {order_type}: {retcode} - {comment_msg}")
                return {
                    "success": False,
                    "retcode": retcode,
                    "error": comment_msg,
                }

    def close_position(self, ticket: int, symbol: str, volume: float, order_type: str) -> dict:
        """Closes an open position by ticket."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")

        with MT5Executor._lock:
            tick = self.mt5.symbol_info_tick(symbol)
            if not tick:
                return {"success": False, "error": f"No quote for {symbol}"}

            sym_info = self.mt5.symbol_info(symbol)
            filling_mode = getattr(sym_info, "filling_mode", 0) if sym_info else 0
            if filling_mode & 2:
                filling_type = getattr(self.mt5, "ORDER_FILLING_IOC", 1)
            elif filling_mode & 1:
                filling_type = getattr(self.mt5, "ORDER_FILLING_FOK", 0)
            else:
                filling_type = getattr(self.mt5, "ORDER_FILLING_RETURN", 2)

            is_buy = order_type.lower() == "buy"
            close_type = getattr(self.mt5, "ORDER_TYPE_SELL", 1) if is_buy else getattr(self.mt5, "ORDER_TYPE_BUY", 0)
            price = float(tick.bid if is_buy else tick.ask)

            remote_code = f"""
import MetaTrader5 as mt5
_close_res = mt5.order_send({{
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': '{symbol}',
    'volume': {float(volume)},
    'type': {close_type},
    'position': {int(ticket)},
    'price': {price},
    'deviation': 20,
    'magic': 100888,
    'comment': 'LiquidityBot Close',
    'type_time': mt5.ORDER_TIME_GTC,
    'type_filling': {filling_type},
}})
"""
            try:
                self._conn.execute(remote_code)
                res = self._conn.namespace.get("_close_res")
            except Exception:
                req = {
                    "action": getattr(self.mt5, "TRADE_ACTION_DEAL", 1),
                    "symbol": symbol,
                    "volume": float(volume),
                    "type": close_type,
                    "position": int(ticket),
                    "price": price,
                    "deviation": 20,
                    "magic": 100888,
                    "comment": "LiquidityBot Close",
                    "type_time": getattr(self.mt5, "ORDER_TIME_GTC", 0),
                    "type_filling": filling_type,
                }
                res = self.mt5.order_send(req)

            if res and getattr(res, "retcode", 0) in [10008, 10009]:
                logger.success(f"Position {ticket} ({symbol}) closed @ {res.price}")
                return {"success": True, "ticket": ticket, "price": res.price}
            else:
                comment_msg = getattr(res, "comment", "Unknown") if res else "Failed"
                return {"success": False, "error": comment_msg}

    def modify_position(
        self,
        ticket: int,
        symbol: str,
        stop_loss: float,
        take_profit: float = 0.0,
    ) -> dict:
        """Modifies Stop Loss and/or Take Profit on an open position."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")

        with MT5Executor._lock:
            sym_info = self.mt5.symbol_info(symbol)
            digits = int(getattr(sym_info, "digits", 5)) if sym_info else 5
            sl = round(float(stop_loss), digits) if stop_loss > 0 else 0.0
            tp = round(float(take_profit), digits) if take_profit > 0 else 0.0

            remote_code = f"""
import MetaTrader5 as mt5
_mod_res = mt5.order_send({{
    'action': mt5.TRADE_ACTION_SLTP,
    'position': {int(ticket)},
    'symbol': '{symbol}',
    'sl': {sl},
    'tp': {tp},
}})
"""
            try:
                self._conn.execute(remote_code)
                res = self._conn.namespace.get("_mod_res")
            except Exception:
                req = {
                    "action": getattr(self.mt5, "TRADE_ACTION_SLTP", 6),
                    "position": int(ticket),
                    "symbol": symbol,
                    "sl": sl,
                    "tp": tp,
                }
                res = self.mt5.order_send(req)

            if res and getattr(res, "retcode", 0) in [10008, 10009]:
                logger.success(f"Position {ticket} ({symbol}) modified: SL={sl}, TP={tp}")
                return {"success": True, "ticket": ticket, "sl": sl, "tp": tp}
            else:
                comment_msg = getattr(res, "comment", "Unknown") if res else "Failed"
                retcode = getattr(res, "retcode", -1) if res else -1
                logger.warning(f"Failed to modify position {ticket} ({symbol}): {retcode} - {comment_msg}")
                return {"success": False, "error": comment_msg, "retcode": retcode}

    def close(self):
        """No-op for pooled connection to prevent dropping active RPC sessions."""
        pass

    @classmethod
    def force_disconnect(cls):
        """Clean shutdown invoked during application termination."""
        with cls._lock:
            if cls._shared_mt5:
                try:
                    cls._shared_mt5.shutdown()
                except Exception:
                    pass
                cls._shared_mt5 = None
            if cls._shared_conn:
                try:
                    cls._shared_conn.close()
                except Exception:
                    pass
                cls._shared_conn = None
            logger.info("MT5 shared connection cleanly terminated.")
