"""
check_analyzer_real_data.py
---------------------------
Tests the MarketAnalyzer on REAL candles (development data only, so the
hold-out stays locked).

Run from the backend folder:
    python scripts/check_analyzer_real_data.py
    python scripts/check_analyzer_real_data.py EURJPY 0.05 0.01
      (symbol, bin_size, pip_size)
    python scripts/check_analyzer_real_data.py SYNTHETIC
      (made-up candles, for trying the script without any data file)

Part 1  NO-PEEKING TEST        does the answer at candle N ignore the future?
Part 2  CHECK IT AGAINST MATHS  recompute the numbers a second, simple way
Part 3  LOOK-AT-A-CHART LIST    moments you can check by eye

Exit code is 0 when every check passes, 1 otherwise.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_analyzer.analyzer import MarketAnalyzer  # noqa: E402
from app.market_analyzer.volume_profile import volume_profile  # noqa: E402

TIMEFRAME = "M15"
MAX_CANDLES = 12000      # about 4 months of M15; keeps the test quick
NUMBER_FIELDS = ("atr", "bb_width", "width_zscore", "vpoc", "value_area_low", "value_area_high")

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"\n         -> {detail}" if detail else ""))


def same_number(a, b, rtol=1e-9):
    """
    True if two numbers are equal (or both empty).
    The default is very strict. The recalculation checks use rtol=1e-6
    because pandas adds and removes numbers from a running total, which
    leaves tiny rounding noise (about 1 part in 100 million).
    """
    if a is None or b is None:
        return a is None and b is None
    return bool(np.isclose(a, b, rtol=rtol, atol=1e-12))


def table_as_list(table):
    """Turns a table into plain Python rows so two tables can be compared safely."""
    rows = []
    for _, row in table.reset_index(drop=True).iterrows():
        rows.append(tuple(None if pd.isna(v) else v for v in row.tolist()))
    return rows


def find_differences(full_state, cut_state):
    problems = []
    for field in NUMBER_FIELDS:
        if not same_number(getattr(full_state, field), getattr(cut_state, field)):
            problems.append(field)

    a, b = full_state.active_levels, cut_state.active_levels
    if list(a.columns) != list(b.columns):
        problems.append("active_levels (different columns)")
    else:
        # Compare the WHOLE table, column by column, so a hidden column
        # carrying future information cannot slip through.
        rows_a, rows_b = table_as_list(a), table_as_list(b)
        if len(rows_a) != len(rows_b):
            problems.append("active_levels (different number of levels)")
        else:
            for column_number, column in enumerate(a.columns):
                if [r[column_number] for r in rows_a] != [r[column_number] for r in rows_b]:
                    problems.append(f"active_levels column '{column}'")
    return problems


def make_synthetic(n=12000, seed=0):
    rng = np.random.default_rng(seed)
    close = 1.1 + np.cumsum(rng.normal(0, 0.0005, n))
    open_ = np.concatenate([[1.1], close[:-1]])
    high = np.maximum(open_, close) + rng.uniform(0, 0.0003, n)
    low = np.minimum(open_, close) - rng.uniform(0, 0.0003, n)
    times = pd.date_range("2023-01-02", periods=n, freq="15min")
    return pd.DataFrame(
        {"time": times, "open": open_, "high": high, "low": low, "close": close,
         "volume": rng.integers(50, 500, n).astype(float), "spread": 12.0}
    )


# ---------------------------------------------------------------
# PART 1: no peeking
# ---------------------------------------------------------------

def part1_no_peeking(work, bin_size):
    print("\nPART 1: No-peeking test")
    print("The answer at candle N must be EXACTLY the same whether the analyzer can")
    print("see the whole file or only candles 0..N. Every column is compared.\n")

    full = MarketAnalyzer(work, bin_size)
    rng = np.random.default_rng(42)
    spots = sorted({5, 30, 150, 400} | {int(p) for p in rng.choice(np.arange(500, len(work)), 25, replace=False)})

    bad = {}
    for at in spots:
        cut = MarketAnalyzer(work.iloc[: at + 1].reset_index(drop=True), bin_size)
        problems = find_differences(full.state_at(at), cut.state_at(at))
        if problems:
            bad[at] = problems

    if bad:
        first_at = next(iter(bad))
        detail = f"{len(bad)} of {len(spots)} spots differ. Example: candle {first_at} -> {bad[first_at]}"
    else:
        detail = ""
    check(f"Same answer with and without the future ({len(spots)} spots)", not bad, detail)

    state = full.state_at(len(work) // 2)
    check(
        "active_levels has no column that talks about the future (swept_at)",
        "swept_at" not in state.active_levels.columns,
        "a level's swept_at is the candle where it WILL be crossed later" if "swept_at" in state.active_levels.columns else "",
    )
    return full


# ---------------------------------------------------------------
# PART 2: recompute everything a second, simple way
# ---------------------------------------------------------------

def brute_swings(high, low, left=2, right=2):
    """Slow, obvious swing finder: compare each candle with its neighbours."""
    swings = set()
    for p in range(left, len(high) - right):
        around_h = [high[p + k] for k in range(-left, right + 1) if k != 0]
        around_l = [low[p + k] for k in range(-left, right + 1) if k != 0]
        if high[p] > max(around_h):
            swings.add((p, "swing_high"))
        if low[p] < min(around_l):
            swings.add((p, "swing_low"))
    return swings


def part2_against_maths(work, analyzer, bin_size, pip):
    print("\nPART 2: Recompute it a second way")

    close = work["close"].to_numpy()
    positions = list(range(300, len(work), 211))

    # ATR: Wilder smoothing written as a plain loop
    tr = np.empty(len(work))
    tr[0] = work["high"].iloc[0] - work["low"].iloc[0]
    prev_close = close[:-1]
    h, l = work["high"].to_numpy()[1:], work["low"].to_numpy()[1:]
    tr[1:] = np.maximum.reduce([h - l, np.abs(h - prev_close), np.abs(l - prev_close)])
    atr_loop = np.empty(len(work))
    atr_loop[0] = tr[0]
    for i in range(1, len(work)):
        atr_loop[i] = atr_loop[i - 1] * (13 / 14) + tr[i] / 14
    atr_ok = all(same_number(analyzer.state_at(i).atr, float(atr_loop[i])) for i in positions)
    check("ATR equals a plain-loop recalculation", atr_ok)

    # Bollinger width = 4 * std / mean over the last 20 closes
    width_ok = True
    for i in positions:
        window = close[i - 19 : i + 1]
        expected = 4 * window.std(ddof=0) / window.mean()
        width_ok &= same_number(analyzer.state_at(i).bb_width, float(expected), rtol=1e-6)
    check("Bollinger width equals 4 x spread / average of the last 20 closes", width_ok)

    # z-score uses the 100 widths BEFORE today
    z_ok = True
    zscore_window = 100
    widths = []
    for i in range(len(work)):
        if i >= 19:
            w = close[i - 19 : i + 1]
            widths.append(4 * w.std(ddof=0) / w.mean())
        else:
            widths.append(np.nan)
    widths = np.array(widths)
    for i in positions:
        past = widths[i - zscore_window : i]
        expected = (widths[i] - past.mean()) / past.std(ddof=0)
        z_ok &= same_number(analyzer.state_at(i).width_zscore, float(expected), rtol=1e-6)
    check("z-score compares today with the 100 widths BEFORE today", z_ok)

    # Swing levels: compare with the slow obvious finder on the first 3000 candles
    small = work.iloc[:3000].reset_index(drop=True)
    small_analyzer = MarketAnalyzer(small, bin_size)
    high, low = small["high"].to_numpy(), small["low"].to_numpy()
    swings = brute_swings(high, low)
    wrong_spots = []
    for at in range(300, len(small), 53):
        expected = set()
        for p, kind in swings:
            if p + 2 > at:
                continue  # not confirmed yet
            if kind == "swing_high" and not (high[p + 1 : at + 1] > high[p]).any():
                expected.add((p, kind))
            if kind == "swing_low" and not (low[p + 1 : at + 1] < low[p]).any():
                expected.add((p, kind))
        got_levels = small_analyzer.state_at(at).active_levels
        got = set(zip(got_levels["position"].astype(int), got_levels["kind"]))
        if got != expected:
            wrong_spots.append((at, len(expected - got), len(got - expected)))
    check(
        "Active levels match a slow, obvious recalculation (3000 candles)",
        not wrong_spots,
        f"first mismatch at candle {wrong_spots[0][0]}: {wrong_spots[0][1]} missing, {wrong_spots[0][2]} extra" if wrong_spots else "",
    )

    # Level data sanity: price matches the candle, never known too early
    level_problems = []
    for at in positions:
        levels = analyzer.state_at(at).active_levels
        if len(levels) == 0:
            continue
        if (levels["known_at"] > at).any():
            level_problems.append(f"candle {at}: a level is used before it is confirmed")
        for _, row in levels.iterrows():
            column = "high" if row["kind"] == "swing_high" else "low"
            if not np.isclose(row["price"], work[column].iloc[int(row["position"])]):
                level_problems.append(f"candle {at}: level price does not match its candle")
                break
    check("Levels are never used early and their prices match their candles", not level_problems, "; ".join(level_problems[:2]))

    # Volume profile properties
    vp_problems = []
    rows = []
    for at in positions:
        state = analyzer.state_at(at)
        recent = work.iloc[max(0, at - analyzer.profile_window + 1) : at + 1]
        profile = volume_profile(recent, bin_size)
        inside = profile[(profile["price_low"] >= state.value_area_low - 1e-12) & (profile["price_high"] <= state.value_area_high + 1e-12)]
        share = inside["volume"].sum() / profile["volume"].sum()
        if share < 0.70 - 1e-9:
            vp_problems.append(f"candle {at}: value area holds only {share:.1%}")
        if not (state.value_area_low <= state.vpoc <= state.value_area_high):
            vp_problems.append(f"candle {at}: VPOC outside the value area")
        if not (recent["low"].min() - bin_size <= state.vpoc <= recent["high"].max() + bin_size):
            vp_problems.append(f"candle {at}: VPOC outside the recent price range")
        rows.append({"atr": state.atr, "z": state.width_zscore, "n": len(state.active_levels)})
    check("Value area holds at least 70% of volume, and VPOC sits inside it", not vp_problems, "; ".join(vp_problems[:2]))

    table = pd.DataFrame(rows)
    check("No empty answers after candle 300", table[["atr", "z"]].notna().all().all())
    check("ATR is always above zero", (table["atr"] > 0).all())
    z = table["z"].dropna()
    print(f"         ATR in pips: middle {table['atr'].median() / pip:.1f}, "
          f"z-score average {z.mean():+.2f}, active levels per moment: middle {table['n'].median():.0f}")

    for bad_at in (-1, len(work)):
        try:
            analyzer.state_at(bad_at)
            check(f"state_at({bad_at}) is rejected", False, "no error was raised")
        except ValueError:
            check(f"state_at({bad_at}) is rejected", True)


# ---------------------------------------------------------------
# PART 3: moments to check on a chart
# ---------------------------------------------------------------

def part3_eyeball(work, analyzer, pip):
    print("\nPART 3: Moments to check on a chart (look these dates up)")
    z = analyzer._zscore.dropna()
    print("\nWildest (corridor much wider than usual):")
    for at, value in z.nlargest(5).items():
        print(f"  {work['time'][at]}   z = {value:+.2f}   ATR = {analyzer._atr.iloc[at] / pip:.1f} pips")
    print("\nQuietest (corridor much narrower than usual):")
    for at, value in z.nsmallest(5).items():
        print(f"  {work['time'][at]}   z = {value:+.2f}   ATR = {analyzer._atr.iloc[at] / pip:.1f} pips")

    mid = len(work) // 2
    state = analyzer.state_at(mid)
    print(f"\nFull picture at {work['time'][mid]} (candle {mid}), close {work['close'][mid]:.5f}:")
    print(f"  ATR {state.atr / pip:.1f} pips | width z-score {state.width_zscore:+.2f}")
    print(f"  VPOC {state.vpoc:.5f} | value area {state.value_area_low:.5f} to {state.value_area_high:.5f}")
    print(f"  {len(state.active_levels)} active levels (nearest 6 to the close):")
    levels = state.active_levels.copy()
    levels["distance_pips"] = (levels["price"] - work["close"][mid]) / pip
    levels = levels.reindex(levels["distance_pips"].abs().sort_values().index).head(6)
    print(levels.to_string(index=False) if len(levels) else "  (none)")


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    bin_size = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0005
    pip = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0001

    if symbol == "SYNTHETIC":
        candles = make_synthetic()
    else:
        from app.data.loader import load_candles  # development data only
        candles = load_candles(symbol, TIMEFRAME)

    work = candles.iloc[:MAX_CANDLES].reset_index(drop=True)
    print(f"Testing {symbol} {TIMEFRAME}: {len(work)} candles, {work['time'].iloc[0]} to {work['time'].iloc[-1]}")

    analyzer = part1_no_peeking(work, bin_size)
    part2_against_maths(work, analyzer, bin_size, pip)
    part3_eyeball(work, analyzer, pip)

    print(f"\n{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()