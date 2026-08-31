class TradeForensics:
    """Reconstructs why a trade happened or why a setup was rejected."""

    def build_case_file(self, trade, events):
        return {
            "trade": trade,
            "events": events,
        }
