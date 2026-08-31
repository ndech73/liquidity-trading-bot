class BacktestEngine:
    """Uses the same strategy/exit rules against historical data."""

    def run(self, candles, strategy, risk):
        raise NotImplementedError
