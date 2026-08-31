def is_expanding(
    candle_range: float,
    baseline_range: float,
    threshold: float = 1.50,
) -> bool:
    return baseline_range > 0 and candle_range / baseline_range >= threshold
