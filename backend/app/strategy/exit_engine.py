class ExitEngine:
    """Exit philosophy: invalidation, target liquidity, structural protection, runner."""

    def evaluate(self, position: dict, context: dict) -> dict:
        return {
            "action": "HOLD",
            "reason": "Exit rules not implemented yet",
        }
