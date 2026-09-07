from app.execution.mt5_executor import MT5Executor
from app.analysis_engine.domain.candle import Timeframe
from app.analysis_engine.multi_market.manager import MultiMarketManager


def main():
    executor = MT5Executor()
    connected = executor.connect()
    print("Connected:", connected)

    if not connected:
        print("Connection failed, stopping.")
        return

    manager = MultiMarketManager(
        executor=executor,
        symbols=[
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
            "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "EURGBP",
        ],
        timeframe=Timeframe.M5,
    )

    manager.refresh_all()

    for symbol, state in manager.states.items():
        print(
            f"{symbol}: {len(state.zones)} zones, "
            f"{len(state.sweep_events)} sweeps, "
            f"volatility={state.latest_volatility}"
        )

    executor.close()


if __name__ == "__main__":
    main()