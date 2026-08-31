class MT5Executor:
    """Thin execution adapter. Strategy and analysis must not live here."""

    def connect(self):
        # Import MetaTrader5 only inside the execution environment.
        import MetaTrader5 as mt5
        return mt5.initialize()

    def close(self):
        import MetaTrader5 as mt5
        mt5.shutdown()
