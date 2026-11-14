"""
final_stats.py
--------------
Evaluates Tests A to E according to RULES_v2.md section 5 (k=12).
"""

from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from app.evaluation.edge_stats import repeat_check, weekly_bootstrap_interval


@dataclass
class FinalEdgeReport:
    k: int
    n_trades: int
    mean_outcome: float
    mean_cost_first: float
    mean_cost_worst: float
    margin_net: float
    interval: Tuple[float, float]
    interval_confidence: float
    beat_fraction: float
    beat_required: float
    pairs_positive: int
    pairs_total: int
    quarter_share_positive: float
    passed: Dict[str, bool]
    verdict: str
    report_text: str = ""

    def __str__(self) -> str:
        return self.report_text


def format_final_report(report: FinalEdgeReport) -> str:
    mark = lambda name: "PASS" if report.passed[name] else "FAIL"
    low, high = report.interval
    lines = [
        f"Trades: {report.n_trades}    ideas tried (k): {report.k}",
        f"Average outcome: {report.mean_outcome:+.4f} ATR    average cost (first): {report.mean_cost_first:.4f} ATR    (worst: {report.mean_cost_worst:.4f} ATR)",
        "",
        f"A  pattern exists   {mark('A')}   {report.interval_confidence:.2%} range: {low:+.4f} to {high:+.4f} (low end must be above 0)",
        f"B  beats costs      {mark('B')}   outcome minus 1.25x cost: {report.margin_net:+.4f} (must be above 0)",
        f"C  beats random     {mark('C')}   beat {report.beat_fraction:.2%} of random runs (need {report.beat_required:.2%})",
        f"D  repeats          {mark('D')}   pairs above 0: {report.pairs_positive}/{report.pairs_total} (need 4), quarters above 0: {report.quarter_share_positive:.0%} (need 70%)",
        f"E  enough data      {mark('E')}   {report.n_trades} trades (need 300)",
        "",
        f"VERDICT: {report.verdict}",
    ]
    return "\n".join(lines)


def final_report(trades: pd.DataFrame, k: int = 12) -> FinalEdgeReport:
    """
    Runs Tests A to E as defined in RULES_v2.md section 5.
    """
    conf = 1.0 - 0.05 / k
    beat_required = 1.0 - 0.01 / k
    n_trades = len(trades)

    if n_trades == 0:
        passed = {t: False for t in "ABCDE"}
        verdict = "NOT ENOUGH DATA: there are no trades"
        rep = FinalEdgeReport(
            k=k,
            n_trades=0,
            mean_outcome=0.0,
            mean_cost_first=0.0,
            mean_cost_worst=0.0,
            margin_net=0.0,
            interval=(0.0, 0.0),
            interval_confidence=conf,
            beat_fraction=0.0,
            beat_required=beat_required,
            pairs_positive=0,
            pairs_total=0,
            quarter_share_positive=0.0,
            passed=passed,
            verdict=verdict,
        )
        rep.report_text = format_final_report(rep)
        return rep

    outcomes = trades["outcome_atr"].to_numpy(dtype=float)
    outcomes_opp = trades["outcome_atr_opposite"].to_numpy(dtype=float)
    mean_outcome = float(outcomes.mean())
    mean_cost_first = float(trades["cost_first_atr"].mean())
    mean_cost_worst = float(trades["cost_worst_atr"].mean())
    margin_net = float(mean_outcome - 1.25 * mean_cost_first)

    # Test A: weekly bootstrap interval (20,000 resamples of whole weeks with year)
    interval = weekly_bootstrap_interval(
        trades["outcome_atr"], trades["week"], confidence=conf, n_boot=20000, seed=0
    )

    # Test B: mean(outcome_atr) - 1.25 x mean(cost_first_atr) > 0
    pass_b = bool(margin_net > 0)

    # Test C: 10,000 random runs with mirrored opposite direction
    real_mean = mean_outcome
    rng = np.random.default_rng(seed=0)
    n_runs = 10000
    chunk = 1000
    beaten = 0
    done = 0
    diff = outcomes - outcomes_opp
    base_mean = float(outcomes_opp.mean())

    while done < n_runs:
        batch = min(chunk, n_runs - done)
        picks = rng.integers(0, 2, size=(batch, n_trades))
        random_means = base_mean + (picks @ diff) / n_trades
        beaten += int((random_means < real_mean).sum())
        done += batch

    beat_fraction = float(beaten / n_runs)
    pass_c = bool(beat_fraction >= beat_required)

    # Test D: repeat check (pairs positive >= 4, quarters positive >= 70%)
    pairs_positive, pairs_total, quarter_share = repeat_check(trades)
    pass_d = bool(pairs_positive >= 4 and quarter_share >= 0.70)

    # Test E: at least 300 trades
    pass_e = bool(n_trades >= 300)

    pass_a = bool(interval[0] > 0)

    passed = {
        "A": pass_a,
        "B": pass_b,
        "C": pass_c,
        "D": pass_d,
        "E": pass_e,
    }

    if not pass_e:
        verdict = f"NOT ENOUGH DATA: only {n_trades} trades (need 300)"
    elif all(passed.values()):
        verdict = "PASSED A-E: run Test F on the hold-out, ONCE"
    else:
        failed = ", ".join(name for name in "ABCDE" if not passed[name])
        verdict = f"NO EDGE FOUND: failed {failed}"

    rep = FinalEdgeReport(
        k=k,
        n_trades=n_trades,
        mean_outcome=mean_outcome,
        mean_cost_first=mean_cost_first,
        mean_cost_worst=mean_cost_worst,
        margin_net=margin_net,
        interval=interval,
        interval_confidence=conf,
        beat_fraction=beat_fraction,
        beat_required=beat_required,
        pairs_positive=pairs_positive,
        pairs_total=pairs_total,
        quarter_share_positive=quarter_share,
        passed=passed,
        verdict=verdict,
    )
    rep.report_text = format_final_report(rep)
    return rep
