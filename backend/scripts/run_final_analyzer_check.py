"""
run_final_analyzer_check.py
---------------------------
The FINAL analyzer test. It runs the checks from check_analyzer_real_data.py
on ALL six pairs and on FIVE slices spread across the WHOLE development
period (30 runs in total), then prints one summary table.

  - Development data only. The hold-out is never loaded.
  - It only READS. It changes no file.
  - A crash counts as a failure, never as a pass.

Run from the backend folder:
    python scripts/run_final_analyzer_check.py

Exit code is 0 only if EVERY run passes every check.
"""

import contextlib
import hashlib
import io
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_analyzer_real_data as check  # noqa: E402
from app.data.loader import HOLDOUT_START, load_candles  # noqa: E402

TIMEFRAME = "M15"
SLICES = 5
SLICE_LENGTH = 12000
EXPECTED_CHECKS = 12  # 2 from Part 1 + 10 from Part 2

# pair -> (bin_size, pip_size)
PAIRS = {
    "EURUSD": (0.0005, 0.0001),
    "GBPUSD": (0.0005, 0.0001),
    "USDCHF": (0.0005, 0.0001),
    "USDCAD": (0.0005, 0.0001),
    "NZDUSD": (0.0005, 0.0001),
    "EURJPY": (0.05, 0.01),
}

ANALYZER_FILES = [
    "app/market_analyzer/analyzer.py",
    "app/market_analyzer/liquidity.py",
    "app/market_analyzer/volatility.py",
    "app/market_analyzer/volume_profile.py",
]


def fingerprint(relative_path):
    """A short code for a file's content, so we know exactly which version was tested."""
    data = (BACKEND / relative_path).read_bytes()
    return hashlib.sha256(data).hexdigest()[:12]


def run_one(work, bin_size, pip):
    """Runs Part 1 and Part 2 on one slice. Returns (passed, total, atr, failures, crash)."""
    check.results.clear()
    buffer = io.StringIO()
    crash = ""
    with contextlib.redirect_stdout(buffer):
        try:
            analyzer = check.part1_no_peeking(work, bin_size)
            check.part2_against_maths(work, analyzer, bin_size, pip)
        except Exception as error:  # a crash is a failure
            crash = f"{type(error).__name__}: {error}"

    text = buffer.getvalue()
    lines = text.splitlines()
    failures = []
    for number, line in enumerate(lines):
        if line.startswith("[FAIL]"):
            detail = lines[number + 1].strip() if number + 1 < len(lines) else ""
            failures.append(f"{line[7:]} {detail}".strip())

    found = re.search(r"ATR in pips: middle ([\d.]+)", text)
    atr = found.group(1) if found else "?"
    return sum(check.results), len(check.results), atr, failures, crash


def main():
    print("FINAL ANALYZER TEST (development data only, hold-out never loaded)")
    print("Analyzer files tested (fingerprints):")
    for path in ANALYZER_FILES:
        print(f"  {path:42s} {fingerprint(path)}")
    print()
    print(f"{'pair':8s} {'slice':5s} {'from':10s} {'to':10s} {'checks':8s} {'ATR pips':9s} result")

    bad_runs = []
    total_runs = 0

    for symbol, (bin_size, pip) in PAIRS.items():
        candles = load_candles(symbol, TIMEFRAME)  # development part only
        if candles["time"].max() >= HOLDOUT_START:
            print(f"STOP: {symbol} contains hold-out data. Nothing was tested.")
            sys.exit(1)
        if len(candles) < SLICE_LENGTH:
            print(f"STOP: {symbol} has only {len(candles)} development candles.")
            sys.exit(1)

        starts = np.linspace(0, len(candles) - SLICE_LENGTH, SLICES).round().astype(int)
        for number, start in enumerate(starts, start=1):
            work = candles.iloc[start : start + SLICE_LENGTH].reset_index(drop=True)
            passed, total, atr, failures, crash = run_one(work, bin_size, pip)
            ok = (passed == total == EXPECTED_CHECKS) and not failures and not crash
            total_runs += 1

            print(
                f"{symbol:8s} {number:<5d} {work['time'].iloc[0]:%Y-%m-%d} "
                f"{work['time'].iloc[-1]:%Y-%m-%d} {passed:>2d} of {total:<2d}  "
                f"{atr:>9s} {'PASS' if ok else 'FAIL'}"
            )
            if not ok:
                bad_runs.append((symbol, number, failures, crash, passed, total))

    print()
    if bad_runs:
        print("FAILED RUNS:")
        for symbol, number, failures, crash, passed, total in bad_runs:
            print(f"  {symbol} slice {number}: {passed} of {total} checks passed")
            for failure in failures:
                print(f"     - {failure}")
            if crash:
                print(f"     - CRASH: {crash}")
        print(f"\nFINAL RESULT: FAIL ({len(bad_runs)} of {total_runs} runs failed)")
        sys.exit(1)

    print(f"FINAL RESULT: PASS (all {total_runs} runs passed every check)")
    sys.exit(0)


if __name__ == "__main__":
    main()
