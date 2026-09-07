"""
Full integration test — exercises every module built so far, in the
order data actually flows through the system:

MT5 connection -> candles -> LiquidityDetector -> VolatilityAnalyzer
-> SweepDetector (candle-based) -> live tick -> SweepDetector (tick-based)
-> MultiMarketManager (all 10 pairs)

Run with: python3 test_integration.py
"""

from app.execution.mt5_executor import MT5Executor
from app.analysis_engine.domain.candle import Timeframe
from app.analysis_engine.liquidity.detector import LiquidityDetector
from app.analysis_engine.liquidity.sweep_detector import SweepDetector
from app.analysis_engine.volatility.analyzer import VolatilityAnalyzer
from app.analysis_engine.multi_market.manager import MultiMarketManager

SYMBOL = "EURUSD"
TIMEFRAME = Timeframe.M5
CANDLE_COUNT = 200

ALL_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
    "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP",
]


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main():
    section("1. MT5 CONNECTION")
    executor = MT5Executor()
    connected = executor.connect()
    print("Connected:", connected)
    if not connected:
        print("Connection failed — stopping here.")
        return

    account = executor.get_account_info()
    print("Account:", account)

    section("2. FETCH CANDLES")
    candles = executor.fetch_candles(SYMBOL, TIMEFRAME, CANDLE_COUNT)
    print(f"Fetched {len(candles)} candles for {SYMBOL}")
    if candles:
        print("First candle:", candles[0])
        print("Last candle: ", candles[-1])
    else:
        print("No candles returned — stopping here.")
        executor.close()
        return

    section("3. LIQUIDITY DETECTOR")
    liquidity_detector = LiquidityDetector()
    zones = liquidity_detector.detect(candles)
    print(f"Detected {len(zones)} liquidity zones")
    for zone in zones[:5]:
        print(" -", zone)
    if len(zones) > 5:
        print(f"   ... and {len(zones) - 5} more")

    section("4. VOLATILITY ANALYZER")
    volatility_analyzer = VolatilityAnalyzer()
    readings = volatility_analyzer.analyze(candles)
    print(f"Computed {len(readings)} volatility readings")
    if readings:
        print("Latest reading:", readings[-1])

    section("5. SWEEP DETECTOR — candle-based")
    sweep_detector = SweepDetector()
    updated_zones, sweep_events = sweep_detector.detect(zones, candles)
    print(f"{len(sweep_events)} candle-based sweep(s) detected")
    for event in sweep_events[:5]:
        print(" -", event)

    section("6. FETCH LIVE TICK")
    tick = executor.fetch_tick(SYMBOL)
    print("Tick:", tick)

    section("7. SWEEP DETECTOR — tick-based")
    tick_zones, tick_events = sweep_detector.detect_tick(updated_zones, tick)
    print(f"{len(tick_events)} tick-based sweep(s) detected on this single tick")
    for event in tick_events:
        print(" -", event)

    section("8. MULTI-MARKET MANAGER — all 10 pairs")
    manager = MultiMarketManager(
        executor=executor,
        symbols=ALL_SYMBOLS,
        timeframe=TIMEFRAME,
    )
    manager.refresh_all()
    for symbol, state in manager.states.items():
        print(
            f"{symbol}: {len(state.zones)} zones, "
            f"{len(state.sweep_events)} sweeps, "
            f"volatility={state.latest_volatility}"
        )

    section("9. MULTI-MARKET MANAGER — single tick pass")
    manager.process_tick(SYMBOL)
    updated_state = manager.states[SYMBOL]
    print(
        f"{SYMBOL} after tick pass: {len(updated_state.zones)} zones, "
        f"{len(updated_state.sweep_events)} total sweeps recorded"
    )

    executor.close()
    section("DONE — all stages completed without unhandled errors")


if __name__ == "__main__":
    main()