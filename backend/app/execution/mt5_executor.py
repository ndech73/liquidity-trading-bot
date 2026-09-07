import os
from typing import Optional
from loguru import logger


class MT5Executor:
    """Thin execution adapter supporting both native Windows MT5 and Linux Wine bridge."""

    def __init__(self, host: str = "127.0.0.1", port: int = 18812):
        self.host = host
        self.port = port
        self.mt5 = None
        self._conn = None

    def connect(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
    ) -> bool:
        """Connects to MT5 terminal natively (on Windows) or via Wine RPC bridge (on Linux)."""
        # 1. Attempt native MetaTrader5 (Windows)
        try:
            import MetaTrader5 as native_mt5
            self.mt5 = native_mt5
            logger.info("Using native Windows MetaTrader5 package.")
        except ImportError:
            # 2. Fall back to Wine RPC bridge (mt5server.exe / rpyc)
            try:
                import rpyc
                logger.info(f"Connecting to Wine MT5 RPC server at {self.host}:{self.port}...")
                self._conn = rpyc.classic.connect(self.host, self.port)
                self._conn._config["sync_request_timeout"] = 60
                self.mt5 = self._conn.modules.MetaTrader5
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

        if login and password and server:
            success = self.mt5.initialize(login=int(login), password=password, server=server)
        else:
            success = self.mt5.initialize()

        if not success:
            last_err = self.mt5.last_error()
            logger.error(f"MT5 initialization failed: {last_err}")
            return False

        terminal = self.mt5.terminal_info()
        logger.success(f"MT5 initialized successfully: {terminal.name} (connected: {terminal.connected})")
        return True

    def get_account_info(self):
        """Fetch live account details."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")
        return self.mt5.account_info()

    def get_terminal_info(self):
        """Fetch terminal state details."""
        if not self.mt5:
            raise RuntimeError("MT5 is not connected. Call connect() first.")
        return self.mt5.terminal_info()

    def close(self):
        """Gracefully shuts down MT5 session and closes bridge connection."""
        if self.mt5:
            self.mt5.shutdown()
        if self._conn:
            self._conn.close()
            self._conn = None
        logger.info("MT5 connection closed.")
