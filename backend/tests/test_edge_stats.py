import numpy as np
import pandas as pd
import pytest

from app.evaluation.edge_stats import (
    evaluate_edge,
    format_report,
    holdout_test,
    interval_confidence,
    random_direction_beat_fraction,
    random_runs_for,
    repeat_check,
    required_beat_fraction,
    weekly_bootstrap_interval,
)

SYMBOLS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY"]


def fake_trades(n, edge, cost=0.05, seed=0):
    """
    Fake trades where we KNOW the true average outcome.

    outcome = edge + noise, spread over 3 years, 6 pairs.
    edge=0.3 is a strong edge; edge=0 is pure luck.
    """
    rng = np.random.default_rng(seed)
    direction = rng.choice([-1, 1], size=n)
    move = direction * edge + rng.normal(0, 1, size=n)

    start = pd.Timestamp("2022-11-01")
    seconds = rng.integers(0, 3 * 365 * 24 * 3600, size=n)
    times = pd.to_datetime(start.value + seconds * 10**9)
    times = pd.Series(times)

    return pd.DataFrame(
        {
            "symbol": rng.choice(SYMBOLS, size=n),
            "entry_time": times,
            "direction": direction,
            "move_atr": move,
            "outcome_atr": direction * move,
            "cost_atr": cost,
            "week": times.dt.to_period("W").astype(str),
            "quarter": times.dt.to_period("Q").astype(str),
        }
    )


# ---------- the pass marks that depend on k ----------

def test_pass_marks_get_stricter_as_more_ideas_are_tried():
    assert interval_confidence(1) == pytest.approx(0.95)
    assert interval_confidence(2) == pytest.approx(0.975)
    assert required_beat_fraction(1) == pytest.approx(0.99)
    assert required_beat_fraction(2) == pytest.approx(0.995)
    assert random_runs_for(10) == 1_000
    assert random_runs_for(11) == 10_000


def test_k_below_one_is_rejected():
    with pytest.raises(ValueError):
        interval_confidence(0)


# ---------- Test A: the weekly bootstrap ----------

def test_interval_surrounds_the_true_average():
    trades = fake_trades(4000, edge=0.2, seed=1)
    low, high = weekly_bootstrap_interval(trades["outcome_atr"], trades["week"], 0.95)
    assert low < 0.2 < high


def test_interval_gets_narrower_with_more_trades():
    small = fake_trades(300, edge=0.2, seed=2)
    large = fake_trades(6000, edge=0.2, seed=2)
    low_s, high_s = weekly_bootstrap_interval(small["outcome_atr"], small["week"], 0.95)
    low_l, high_l = weekly_bootstrap_interval(large["outcome_atr"], large["week"], 0.95)
    assert (high_l - low_l) < (high_s - low_s)


def test_higher_confidence_gives_a_wider_interval():
    trades = fake_trades(2000, edge=0.1, seed=3)
    low95, high95 = weekly_bootstrap_interval(trades["outcome_atr"], trades["week"], 0.95)
    low975, high975 = weekly_bootstrap_interval(trades["outcome_atr"], trades["week"], 0.975)
    assert (high975 - low975) > (high95 - low95)


def test_interval_stays_inside_the_weekly_averages():
    # Ten weeks, every trade in week w has outcome w (1..10). The average is 5.5.
    weeks = np.repeat([f"w{i:02d}" for i in range(1, 11)], 5)
    outcomes = np.repeat(np.arange(1.0, 11.0), 5)
    low, high = weekly_bootstrap_interval(outcomes, weeks, 0.95, n_boot=3000)
    assert 1.0 <= low < 5.5 < high <= 10.0


def test_interval_is_repeatable_with_the_same_seed():
    trades = fake_trades(500, edge=0.1, seed=4)
    first = weekly_bootstrap_interval(trades["outcome_atr"], trades["week"], seed=7)
    second = weekly_bootstrap_interval(trades["outcome_atr"], trades["week"], seed=7)
    assert first == second


# ---------- Test C: random directions ----------

def test_a_big_real_edge_beats_nearly_all_random_runs():
    trades = fake_trades(1000, edge=0.4, seed=5)
    fraction, real = random_direction_beat_fraction(trades["move_atr"], trades["direction"])
    assert fraction >= 0.999
    assert real > 0.3


def test_the_opposite_direction_beats_almost_none():
    trades = fake_trades(1000, edge=0.4, seed=5)
    fraction, _ = random_direction_beat_fraction(trades["move_atr"], -trades["direction"])
    assert fraction <= 0.001


def test_random_runs_are_repeatable_with_the_same_seed():
    trades = fake_trades(300, edge=0.0, seed=6)
    first = random_direction_beat_fraction(trades["move_atr"], trades["direction"], seed=9)
    second = random_direction_beat_fraction(trades["move_atr"], trades["direction"], seed=9)
    assert first == second


# ---------- Test D: pairs and quarters ----------

def test_repeat_check_matches_hand_calculation():
    trades = pd.DataFrame(
        {
            "symbol": ["A", "A", "B", "B", "C", "C"],
            "quarter": ["2024Q1", "2024Q2", "2024Q1", "2024Q2", "2024Q1", "2024Q2"],
            "outcome_atr": [1.0, 1.0, -1.0, -0.5, 0.5, 0.2],
        }
    )
    pairs_positive, pairs_total, quarter_share = repeat_check(trades)

    # Pair averages: A = 1.0, B = -0.75, C = 0.35 -> 2 of 3 are above zero.
    assert (pairs_positive, pairs_total) == (2, 3)
    # Quarter averages: Q1 = (1 - 1 + 0.5)/3 = 0.167, Q2 = (1 - 0.5 + 0.2)/3 = 0.233 -> both above 0.
    assert quarter_share == pytest.approx(1.0)


# ---------- Test F: the hold-out ----------

def test_holdout_needs_the_same_direction_and_half_the_size():
    assert holdout_test(0.20, [0.12, 0.12])["passed"] is True
    assert holdout_test(0.20, [0.05, 0.05])["passed"] is False   # too small
    assert holdout_test(0.20, [-0.10, -0.10])["passed"] is False  # wrong direction
    assert holdout_test(-0.05, [0.30, 0.30])["passed"] is False   # there was no edge to confirm


# ---------- all of A to E together ----------

def test_strong_edge_passes_everything():
    report = evaluate_edge(fake_trades(3000, edge=0.3, seed=10), k=1, n_boot=2000)
    assert all(report.passed.values())
    assert report.verdict.startswith("PASSED")


def test_pure_luck_never_passes():
    for seed in range(30):
        report = evaluate_edge(fake_trades(1500, edge=0.0, seed=seed), k=1, n_boot=500)
        assert not all(report.passed.values()), f"seed {seed} passed by luck"
        assert not report.verdict.startswith("PASSED")


def test_a_real_but_tiny_edge_that_costs_eat_fails_test_b():
    trades = fake_trades(30000, edge=0.05, cost=0.30, seed=11)
    report = evaluate_edge(trades, k=1, n_boot=1000)
    assert report.passed["A"] is True      # the pattern exists...
    assert report.passed["B"] is False     # ...but costs eat it
    assert "B" in report.verdict


def test_too_few_trades_is_not_enough_data_even_with_a_big_edge():
    report = evaluate_edge(fake_trades(200, edge=0.5, seed=12), k=1, n_boot=500)
    assert report.passed["E"] is False
    assert report.verdict.startswith("NOT ENOUGH DATA")


def test_no_trades_does_not_crash():
    report = evaluate_edge(fake_trades(10, edge=0.0).iloc[0:0], k=1)
    assert report.verdict.startswith("NOT ENOUGH DATA")
    assert not any(report.passed.values())


def test_the_second_idea_faces_a_wider_range_and_a_higher_bar():
    trades = fake_trades(3000, edge=0.3, seed=13)
    first = evaluate_edge(trades, k=1, n_boot=2000)
    second = evaluate_edge(trades, k=2, n_boot=2000)

    assert second.interval[0] < first.interval[0]
    assert second.beat_required > first.beat_required


def test_the_report_text_shows_every_test_and_the_verdict():
    text = format_report(evaluate_edge(fake_trades(1000, edge=0.3, seed=14), k=1, n_boot=500))
    for label in ["A  pattern exists", "B  beats costs", "C  beats random",
                  "D  repeats", "E  enough data", "VERDICT"]:
        assert label in text
