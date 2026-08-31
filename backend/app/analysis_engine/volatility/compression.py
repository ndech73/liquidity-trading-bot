def is_compressed(
    recent_ranges: list[float],
    baseline_ranges: list[float],
    threshold: float = 0.70,
) -> bool:
    if not recent_ranges or not baseline_ranges:
        return False

    recent_avg = sum(recent_ranges) / len(recent_ranges)
    baseline_avg = sum(baseline_ranges) / len(baseline_ranges)

    return baseline_avg > 0 and recent_avg / baseline_avg < threshold
