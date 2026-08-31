class MultiMarketAnalyzer:
    def __init__(self, factory):
        self.factory = factory
        self.engines = {}

    def get(self, symbol: str, timeframe: str):
        key = f"{symbol}:{timeframe}"
        if key not in self.engines:
            self.engines[key] = self.factory()
        return self.engines[key]
