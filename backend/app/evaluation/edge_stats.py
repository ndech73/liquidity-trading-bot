"""
edge_stats.py
-------------
The edge tests from RULES.md section 4 (Tests A to F).

Everything here takes a table of TRADES (made by outcomes.build_trades,
for all pairs put together) with these columns:
    symbol, entry_time, direction, move_atr, outcome_atr, cost_atr,
    week, quarter

IMPORTANT: these tools only measure. The pass marks come from RULES.md and
are written down here as numbers so nobody can bend them after a result.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Pass marks that do not depend on k (RULES.md section 4)
MIN_TRADES = 300
MIN_PAIRS_POSITIVE = 4
MIN_QUARTER_SHARE = 0.70
HOLDOUT_MIN_SIZE_SHARE = 0.5


# ---------------------------------------------------------------
# Pass marks that get stricter as more ideas are tried (RULES.md section 6)
# ---------------------------------------------------------------

def _check_k(k: int) -> None:
    if k < 1:
        raise ValueError("k (the number of ideas tried) must be at least 1")


def interval_confidence(k: int) -> float:
    """Test A: (100 - 5/k)%.  k=1 -> 95%,  k=2 -> 97.5%."""
    _check_k(k)
    return 1 - 0.05 / k


def required_beat_fraction(k: int) -> float:
    """Test C: (100 - 1/k)%.  k=1 -> 99%,  k=2 -> 99.5%."""
    _check_k(k)
    return 1 - 0.01 / k


def random_runs_for(k: int) -> int:
    """Test C: 1,000 random runs, or 10,000 once k is above 10."""
    _check_k(k)
    return 10_000 if k > 10 else 1_000


# ---------------------------------------------------------------
# Test A: does the pattern exist?
# ---------------------------------------------------------------

def weekly_bootstrap_interval(
    outcomes, weeks, confidence: float = 0.95, n_boot: int = 5000, seed: int = 0
):
    """
    A range for the true average outcome.

    We copy the trades into many "pretend histories". Each pretend
    history is made by drawing WHOLE WEEKS (with repeats) from the real
    weeks. Whole weeks are used because trades in the same week are not
    independent, and drawing single trades would make us too sure.

    Returns (low, high). Test A passes when `low` is above zero.
    """
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

    frame = pd.DataFrame({"outcome": np.asarray(outcomes, dtype=float), "week": np.asarray(weeks)})
    per_week = frame.groupby("week")["outcome"].agg(["sum", "count"])
    sums = per_week["sum"].to_numpy()
    counts = per_week["count"].to_numpy()
    n_weeks = len(per_week)

    rng = np.random.default_rng(seed)
    picks = rng.integers(0, n_weeks, size=(n_boot, n_weeks))
    means = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)

    tail = (1 - confidence) / 2
    return float(np.quantile(means, tail)), float(np.quantile(means, 1 - tail))


# ---------------------------------------------------------------
# Test C: does it beat random?
# ---------------------------------------------------------------

def random_direction_beat_fraction(
    move_atr, direction, n_runs: int = 1000, seed: int = 0, chunk: int = 500
):
    """
    Keeps the same entries and the same price moves, but gives every trade
    a random direction (long or short by coin flip). Does that 1,000 times.

    Returns (share of random runs that the real result beat, real average).
    A real edge should beat almost all of them.
    """
    move = np.asarray(move_atr, dtype=float)
    real_mean = float(np.mean(np.asarray(direction, dtype=float) * move))

    rng = np.random.default_rng(seed)
    beaten = 0
    done = 0
    while done < n_runs:
        batch = min(chunk, n_runs - done)
        signs = rng.choice([-1.0, 1.0], size=(batch, len(move)))
        random_means = (signs * move).mean(axis=1)
        beaten += int((random_means < real_mean).sum())
        done += batch

    return beaten / n_runs, real_mean


# ---------------------------------------------------------------
# Test D: does it repeat?
# ---------------------------------------------------------------

def repeat_check(trades: pd.DataFrame):
    """
    Average outcome (before costs) per pair and per calendar quarter.

    Returns (pairs_positive, pairs_total, share_of_quarters_positive).
    """
    by_pair = trades.groupby("symbol")["outcome_atr"].mean()
    by_quarter = trades.groupby("quarter")["outcome_atr"].mean()
    return (
        int((by_pair > 0).sum()),
        int(len(by_pair)),
        float((by_quarter > 0).mean()),
    )


# ---------------------------------------------------------------
# Test F: the hold-out (run ONCE, at the very end)
# ---------------------------------------------------------------

def holdout_test(dev_mean_outcome: float, holdout_outcomes) -> dict:
    """
    Passes when the hold-out average is above zero AND at least half as
    big as the average on development data.
    """
    holdout_mean = float(np.mean(np.asarray(holdout_outcomes, dtype=float)))
    passed = (
        dev_mean_outcome > 0
        and holdout_mean > 0
        and holdout_mean >= HOLDOUT_MIN_SIZE_SHARE * dev_mean_outcome
    )
    return {"passed": bool(passed), "holdout_mean": holdout_mean}


# ---------------------------------------------------------------
# Tests A to E together
# ---------------------------------------------------------------

@dataclass
class EdgeReport:
    k: int
    n_trades: int
    mean_outcome: float
    mean_cost: float
    interval: tuple
    interval_confidence: float
    beat_fraction: float
    beat_required: float
    pairs_positive: int
    pairs_total: int
    quarter_share_positive: float
    passed: dict = field(default_factory=dict)  # "A".."E" -> True / False
    verdict: str = ""


def evaluate_edge(trades: pd.DataFrame, k: int = 1, seed: int = 0, n_boot: int = 5000) -> EdgeReport:
    """Runs Tests A to E on development-data trades."""
    _check_k(k)
    confidence = interval_confidence(k)
    needed = required_beat_fraction(k)

    if len(trades) == 0:
        report = EdgeReport(
            k=k, n_trades=0, mean_outcome=0.0, mean_cost=0.0,
            interval=(0.0, 0.0), interval_confidence=confidence,
            beat_fraction=0.0, beat_required=needed,
            pairs_positive=0, pairs_total=0, quarter_share_positive=0.0,
            passed={t: False for t in "ABCDE"},
        )
        report.verdict = "NOT ENOUGH DATA: there are no trades"
        return report

    outcomes = trades["outcome_atr"].to_numpy(dtype=float)
    mean_outcome = float(outcomes.mean())
    mean_cost = float(trades["cost_atr"].mean())

    interval = weekly_bootstrap_interval(
        outcomes, trades["week"], confidence=confidence, n_boot=n_boot, seed=seed
    )
    beat_fraction, _ = random_direction_beat_fraction(
        trades["move_atr"], trades["direction"], n_runs=random_runs_for(k), seed=seed
    )
    pairs_positive, pairs_total, quarter_share = repeat_check(trades)

    passed = {
        "A": interval[0] > 0,
        "B": (mean_outcome - mean_cost) > 0,
        "C": beat_fraction >= needed,
        "D": pairs_positive >= MIN_PAIRS_POSITIVE and quarter_share >= MIN_QUARTER_SHARE,
        "E": len(trades) >= MIN_TRADES,
    }
    passed = {name: bool(value) for name, value in passed.items()}

    if not passed["E"]:
        verdict = f"NOT ENOUGH DATA: only {len(trades)} trades (need {MIN_TRADES})"
    elif all(passed.values()):
        verdict = "PASSED A-E: run Test F on the hold-out, ONCE"
    else:
        failed = ", ".join(name for name, ok in passed.items() if not ok)
        verdict = f"NO EDGE FOUND: failed {failed}"

    return EdgeReport(
        k=k, n_trades=len(trades), mean_outcome=mean_outcome, mean_cost=mean_cost,
        interval=interval, interval_confidence=confidence,
        beat_fraction=beat_fraction, beat_required=needed,
        pairs_positive=pairs_positive, pairs_total=pairs_total,
        quarter_share_positive=quarter_share, passed=passed, verdict=verdict,
    )


def format_report(report: EdgeReport) -> str:
    """A plain-text summary, ready to print and to copy into the Test Log."""
    mark = lambda name: "PASS" if report.passed[name] else "FAIL"
    low, high = report.interval
    lines = [
        f"Trades: {report.n_trades}    ideas tried (k): {report.k}",
        f"Average outcome: {report.mean_outcome:+.4f} ATR    average cost: {report.mean_cost:.4f} ATR",
        "",
        f"A  pattern exists   {mark('A')}   {report.interval_confidence:.1%} range: {low:+.4f} to {high:+.4f} (low end must be above 0)",
        f"B  beats costs      {mark('B')}   outcome minus cost: {report.mean_outcome - report.mean_cost:+.4f} (must be above 0)",
        f"C  beats random     {mark('C')}   beat {report.beat_fraction:.1%} of random runs (need {report.beat_required:.1%})",
        f"D  repeats          {mark('D')}   pairs above 0: {report.pairs_positive}/{report.pairs_total} (need {MIN_PAIRS_POSITIVE}), quarters above 0: {report.quarter_share_positive:.0%} (need {MIN_QUARTER_SHARE:.0%})",
        f"E  enough data      {mark('E')}   {report.n_trades} trades (need {MIN_TRADES})",
        "",
        f"VERDICT: {report.verdict}",
    ]
    return "\n".join(lines)
