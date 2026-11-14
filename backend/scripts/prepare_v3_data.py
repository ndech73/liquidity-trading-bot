"""
prepare_v3_data.py
------------------
Executes Step 3 (D1 Data Checks), Step 4 (Cost Table), and Step 5 (Swap Table)
for RULES_v3.md.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.data.loader import load_candles
from app.evaluation.outcomes import point_size

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "NZDUSD", "EURJPY"]
MQL5_WEEKDAYS = {
    0: "Sunday",
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
}


def run_step3_data_checks():
    print("=" * 80)
    print("STEP 3: DAILY (D1) DATA CHECKS (Development Data Only)")
    print("=" * 80)

    rows = []
    stop_for_weekend = False
    weekend_details = {}

    for symbol in PAIRS:
        # Default load_candles() loads DEVELOPMENT part only
        candles = load_candles(symbol, "D1")
        times = candles["time"]

        first_date = times.iloc[0].strftime("%Y-%m-%d")
        last_dev_date = times.iloc[-1].strftime("%Y-%m-%d")
        n_total = len(candles)

        part1_count = int((times < "2022-10-01").sum())
        part2_count = int((times >= "2022-10-01").sum())

        # Weekend candles check: Saturday=5, Sunday=6
        day_of_week = times.dt.day_of_week
        weekend_mask = day_of_week.isin([5, 6])
        n_weekend = int(weekend_mask.sum())
        if n_weekend > 0:
            stop_for_weekend = True
            weekend_details[symbol] = times[weekend_mask].dt.strftime("%Y-%m-%d").tolist()

        # Gaps of more than 4 calendar days
        time_diffs = times.diff()
        gaps_over_4d_mask = time_diffs > pd.Timedelta(days=4)
        n_gaps_over_4d = int(gaps_over_4d_mask.sum())

        gap_records = []
        for idx in times[gaps_over_4d_mask].index:
            from_t = times.loc[idx - 1]
            to_t = times.loc[idx]
            gap_days = (to_t - from_t).days
            gap_records.append((gap_days, from_t.strftime("%Y-%m-%d"), to_t.strftime("%Y-%m-%d")))

        gap_records.sort(key=lambda x: x[0], reverse=True)
        top5_gaps = gap_records[:5]

        starts_after_2005 = times.iloc[0] > pd.Timestamp("2005-01-01")

        rows.append(
            {
                "symbol": symbol,
                "first_date": first_date,
                "last_dev_date": last_dev_date,
                "n_total": n_total,
                "part1": part1_count,
                "part2": part2_count,
                "n_weekend": n_weekend,
                "n_gaps_over_4d": n_gaps_over_4d,
                "top5_gaps": top5_gaps,
                "starts_after_2005": starts_after_2005,
            }
        )

    # Print summary table
    print(f"{'Pair':8s} {'First Date':12s} {'Last Dev Date':14s} {'Total D1':9s} {'Part 1 (<2022)':15s} {'Part 2 (>=2022)':16s} {'Weekend':8s} {'Gaps >4d':9s} {'Later than 2005?':17s}")
    print("-" * 115)
    for r in rows:
        later_str = f"Yes ({r['first_date']})" if r["starts_after_2005"] else "No (2005-01-01)"
        print(f"{r['symbol']:8s} {r['first_date']:12s} {r['last_dev_date']:14s} {r['n_total']:<9d} {r['part1']:<15d} {r['part2']:<16d} {r['n_weekend']:<8d} {r['n_gaps_over_4d']:<9d} {later_str:17s}")

    print("\n--- 5 BIGGEST GAPS PER PAIR (> 4 calendar days) ---")
    for r in rows:
        print(f"{r['symbol']} ({r['n_gaps_over_4d']} total gaps > 4d):")
        if r["top5_gaps"]:
            for days, d_from, d_to in r["top5_gaps"]:
                print(f"   - {days} days: {d_from} -> {d_to}")
        else:
            print("   - None")

    if stop_for_weekend:
        print("\n" + "!" * 80)
        print("ALERT FOR USER / RULES_v3.md: Weekend candles detected!")
        for sym, dates in weekend_details.items():
            print(f"  {sym}: {len(dates)} weekend candles: {dates}")
        print("!" * 80)

    print("\nData check finished.")
    return rows


def run_step4_cost_table():
    print("\n" + "=" * 80)
    print("STEP 4: SPREAD COST TABLE (M15 Development Data, Server Hours 02-23)")
    print("=" * 80)

    cost_data = {
        "rule": "median M15 spread in points, server hours 02-23, development data only",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pairs": {},
    }

    print(f"{'Pair':8s} {'Median Spread (pts)':21s} {'Candles Used':14s} {'First Date':18s} {'Last Date':18s}")
    print("-" * 85)

    for symbol in PAIRS:
        m15 = load_candles(symbol, "M15")  # Defaults = development data
        hours = m15["time"].dt.hour
        # server hours 02:00 to 23:59
        filtered = m15[hours.between(2, 23)]

        med_spread = float(filtered["spread"].median())
        n_candles = len(filtered)
        first_date = filtered["time"].iloc[0].strftime("%Y-%m-%d %H:%M")
        last_date = filtered["time"].iloc[-1].strftime("%Y-%m-%d %H:%M")

        cost_data["pairs"][symbol] = {
            "median_spread_points": med_spread,
            "candles_used": n_candles,
            "first_date": first_date,
            "last_date": last_date,
        }

        print(f"{symbol:8s} {med_spread:<21.1f} {n_candles:<14,d} {first_date:18s} {last_date:18s}")

    cost_file = BACKEND / "data_files" / "cost_table_v3.json"
    cost_file.write_text(json.dumps(cost_data, indent=2))
    print(f"\nSaved cost table to {cost_file}")
    return cost_data


def run_step5_swap_table():
    print("\n" + "=" * 80)
    print("STEP 5: SWAP TABLE (MT5 Live Bridge Query on 127.0.0.1:18812)")
    print("=" * 80)

    import rpyc

    conn = rpyc.classic.connect("127.0.0.1", 18812)
    mt5 = conn.modules.MetaTrader5

    swap_data = {
        "rule": "today's demo swap values, in points per lot per night, used for all years",
        "reading_time": datetime.now(timezone.utc).isoformat(),
        "pairs": {},
    }

    try:
        if not mt5.initialize():
            raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")

        print(f"{'Pair':8s} {'Swap Long':11s} {'Swap Short':12s} {'Swap Mode':11s} {'3-Day Rollover':16s} {'Point':10s} {'Point Check':12s}")
        print("-" * 85)

        for symbol in PAIRS:
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"MT5 does not recognize symbol {symbol}")

            info = mt5.symbol_info(symbol)
            if info is None:
                raise RuntimeError(f"Could not read symbol info for {symbol}")

            swap_mode = int(info.swap_mode)
            expected_swap_mode = int(mt5.SYMBOL_SWAP_MODE_POINTS)
            if swap_mode != expected_swap_mode:
                print(f"STOPPING: {symbol} swap_mode ({swap_mode}) != SYMBOL_SWAP_MODE_POINTS ({expected_swap_mode})")
                sys.exit(1)

            rollover_raw = int(info.swap_rollover3days)
            rollover_name = MQL5_WEEKDAYS.get(rollover_raw, f"Unknown({rollover_raw})")

            mt5_point = float(info.point)
            proj_point = point_size(symbol)
            if abs(mt5_point - proj_point) > 1e-9:
                print(f"STOPPING: {symbol} point mismatch! MT5={mt5_point}, point_size()={proj_point}")
                sys.exit(1)

            swap_long = float(info.swap_long)
            swap_short = float(info.swap_short)

            swap_data["pairs"][symbol] = {
                "swap_mode": "points",
                "swap_mode_raw": swap_mode,
                "swap_long": swap_long,
                "swap_short": swap_short,
                "swap_rollover3days_raw": rollover_raw,
                "swap_rollover3days_name": rollover_name,
                "point": mt5_point,
            }

            print(f"{symbol:8s} {swap_long:>+10.3f} {swap_short:>+11.3f} {'points':11s} {f'{rollover_raw} ({rollover_name})':16s} {mt5_point:<10.5f} {'MATCH':12s}")

        swap_file = BACKEND / "data_files" / "swap_table_v3.json"
        swap_file.write_text(json.dumps(swap_data, indent=2))
        print(f"\nSaved swap table to {swap_file}")
        return swap_data

    finally:
        try:
            mt5.shutdown()
        finally:
            conn.close()


def main():
    run_step3_data_checks()
    run_step4_cost_table()
    run_step5_swap_table()
    print("\nSteps 3, 4, and 5 completed successfully.")


if __name__ == "__main__":
    main()
