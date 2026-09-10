from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.analysis_engine.domain.candle import Candle, Timeframe
from app.analysis_engine.domain.events import LiquiditySweepEvent
from app.analysis_engine.domain.liquidity import LiquiditySide, LiquidityStatus, LiquidityType, LiquidityZone
from app.analysis_engine.engine import MarketSnapshot
from app.analysis_engine.structure.analyzer import MarketStructureTrend
from app.analysis_engine.volatility.analyzer import VolatilityReading, VolatilityRegime
from app.db.models.trade import TradeModel
from app.risk.risk_engine import RiskAssessment, RiskEngine
from app.strategy.entry_engine import EntryEngine, EntrySignal, TradeDirection
from app.strategy.exit_engine import ExitEngine, ExitLevels
from app.strategy.trading_runner import TradingRunner


@pytest.fixture
def sample_candles():
    now = datetime(2026, 9, 9, 8, 0, tzinfo=timezone.utc)
    return [
        Candle(
            symbol="EURUSD",
            timeframe=Timeframe.M5,
            timestamp=datetime.fromtimestamp(now.timestamp() + i * 300, tz=timezone.utc),
            open=1.1000 + i * 0.0001,
            high=1.1010 + i * 0.0001,
            low=1.0995 + i * 0.0001,
            close=1.1005 + i * 0.0001,
            volume=100.0,
        )
        for i in range(40)
    ]


def test_trading_runner_init():
    runner = TradingRunner(watchlist=["EURUSD", "GBPUSD"], poll_interval_seconds=5.0)
    assert runner.watchlist == ["EURUSD", "GBPUSD"]
    assert runner.poll_interval_seconds == 5.0
    assert not runner._is_running


def test_trading_runner_sync_positions():
    runner = TradingRunner(watchlist=["EURUSD"])
    runner.executor = MagicMock()
    # MT5 has no open positions currently
    runner.executor.get_positions.return_value = []
    # Position deals for ticket 12345
    runner.executor.get_position_deals.return_value = [
        {"entry": 1, "price": 1.1050, "profit": 25.0, "swap": 0.0, "commission": -1.0}
    ]

    mock_trade = TradeModel(
        ticket=12345,
        symbol="EURUSD",
        order_type="BUY",
        lots=0.01,
        open_price=1.1020,
        profit=0.0,
        status="OPEN",
        opened_at=datetime.now(timezone.utc),
    )

    with patch("app.strategy.trading_runner.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter_by.return_value.all.return_value = [mock_trade]

        runner.sync_positions()

        assert mock_trade.status == "CLOSED"
        assert mock_trade.close_price == 1.1050
        assert mock_trade.profit == 24.0
        mock_db.commit.assert_called_once()


def test_trading_runner_process_symbol_executes_trade(sample_candles):
    runner = TradingRunner(watchlist=["EURUSD"])
    runner.executor = MagicMock()
    runner.executor.fetch_candles.return_value = sample_candles
    runner.executor.mt5.symbol_info_tick.return_value = MagicMock(ask=1.1040, bid=1.1038)
    runner.executor.get_account_info.return_value = MagicMock(margin_free=100.0, balance=100.0)

    mock_signal = EntrySignal(
        symbol="EURUSD",
        timeframe=Timeframe.M5,
        direction=TradeDirection.BUY,
        signal_time=sample_candles[-2].timestamp,
        entry_price=1.1035,
        stop_loss=1.1000,
        zone_id="test-zone-1",
        liquidity_type=LiquidityType.SWING_LOW,
        level_price=1.1005,
        sweep_price=1.0995,
        trend=MarketStructureTrend.BULLISH,
        expansion_confirmed=True,
        compression_confirmed=False,
    )

    runner.analysis_engine = MagicMock()
    runner.analysis_engine.analyze.return_value = MarketSnapshot(
        symbol="EURUSD",
        candles_analyzed=len(sample_candles),
        zones=[],
        sweep_events=[],
        volatility=None,
        compression=None,
        expansion=None,
    )

    runner.entry_engine = MagicMock()
    runner.entry_engine.evaluate.return_value = [mock_signal]

    runner.risk_engine = MagicMock()
    runner.risk_engine.check.return_value = RiskAssessment(approved=True, reason="Approved", lot_size=0.01)

    runner.executor.open_order.return_value = {
        "success": True,
        "ticket": 999888,
        "price": 1.1040,
    }

    with patch("app.strategy.trading_runner.SessionLocal") as mock_session_local:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        open_symbols = set()
        runner.process_symbol(
            symbol="EURUSD",
            account_dict={"balance": 100.0, "margin_free": 100.0},
            open_positions=[],
            open_symbols=open_symbols,
            scan_for_entries=True,
        )

        assert runner.executor.open_order.call_count == 2
        assert "EURUSD" in open_symbols
        assert mock_db.add.call_count == 2
        assert mock_db.commit.call_count == 2


def test_exit_engine_1_to_3_ratio_default():
    engine = ExitEngine()  # default risk_reward_ratio=3.0, take_profit_pips=None

    # BUY: entry 1.1000, sl 1.0970 -> risk 0.0030 -> tp = 1.1000 + 3*0.0030 = 1.1090
    signal_buy = EntrySignal(
        symbol="EURUSD",
        timeframe=Timeframe.M5,
        direction=TradeDirection.BUY,
        signal_time=datetime.now(timezone.utc),
        entry_price=1.1000,
        stop_loss=1.0970,
        zone_id="z1",
        liquidity_type=LiquidityType.SWING_LOW,
        level_price=1.0975,
        sweep_price=1.0965,
        trend=MarketStructureTrend.BULLISH,
        expansion_confirmed=True,
        compression_confirmed=False,
    )
    exits_buy = engine.compute_exit_levels(signal_buy)
    assert exits_buy.risk_reward_ratio == 3.0
    assert round(exits_buy.take_profit, 5) == 1.1090

    # SELL: entry 1.1000, sl 1.1030 -> risk 0.0030 -> tp = 1.1000 - 3*0.0030 = 1.0910
    signal_sell = EntrySignal(
        symbol="EURUSD",
        timeframe=Timeframe.M5,
        direction=TradeDirection.SELL,
        signal_time=datetime.now(timezone.utc),
        entry_price=1.1000,
        stop_loss=1.1030,
        zone_id="z2",
        liquidity_type=LiquidityType.SWING_HIGH,
        level_price=1.1025,
        sweep_price=1.1035,
        trend=MarketStructureTrend.BEARISH,
        expansion_confirmed=True,
        compression_confirmed=False,
    )
    exits_sell = engine.compute_exit_levels(signal_sell)
    assert exits_sell.risk_reward_ratio == 3.0
    assert round(exits_sell.take_profit, 5) == 1.0910


def test_exit_engine_100_pips_tp():
    engine = ExitEngine(take_profit_pips=100.0)

    # EURUSD (1 pip = 0.0001, 100 pips = 0.0100)
    signal_buy = EntrySignal(
        symbol="EURUSD",
        timeframe=Timeframe.M5,
        direction=TradeDirection.BUY,
        signal_time=datetime.now(timezone.utc),
        entry_price=1.1000,
        stop_loss=1.0970,
        zone_id="z1",
        liquidity_type=LiquidityType.SWING_LOW,
        level_price=1.0975,
        sweep_price=1.0965,
        trend=MarketStructureTrend.BULLISH,
        expansion_confirmed=True,
        compression_confirmed=False,
    )
    exits_buy = engine.compute_exit_levels(signal_buy)
    assert round(exits_buy.take_profit, 5) == 1.1100

    signal_sell = EntrySignal(
        symbol="EURUSD",
        timeframe=Timeframe.M5,
        direction=TradeDirection.SELL,
        signal_time=datetime.now(timezone.utc),
        entry_price=1.1000,
        stop_loss=1.1030,
        zone_id="z2",
        liquidity_type=LiquidityType.SWING_HIGH,
        level_price=1.1025,
        sweep_price=1.1035,
        trend=MarketStructureTrend.BEARISH,
        expansion_confirmed=True,
        compression_confirmed=False,
    )
    exits_sell = engine.compute_exit_levels(signal_sell)
    assert round(exits_sell.take_profit, 5) == 1.0900

    # USDJPY (1 pip = 0.01, 100 pips = 1.00)
    signal_jpy = EntrySignal(
        symbol="USDJPY",
        timeframe=Timeframe.M5,
        direction=TradeDirection.BUY,
        signal_time=datetime.now(timezone.utc),
        entry_price=153.00,
        stop_loss=152.50,
        zone_id="z3",
        liquidity_type=LiquidityType.SWING_LOW,
        level_price=152.60,
        sweep_price=152.40,
        trend=MarketStructureTrend.BULLISH,
        expansion_confirmed=True,
        compression_confirmed=False,
    )
    exits_jpy = engine.compute_exit_levels(signal_jpy)
    assert round(exits_jpy.take_profit, 3) == 154.00


def test_risk_engine_005_lot_defaults():
    engine = RiskEngine()
    assert engine.default_lot_size == 0.05
    assert engine.min_lot_size == 0.05
    assert engine.max_open_trades == 10
    assert engine.max_trades_per_symbol == 2

    # Check assessment lot size
    signal = MagicMock(symbol="EURUSD", entry_price=1.1000, stop_loss=1.0970)
    res = engine.check(signal=signal, account={"balance": 10.0, "margin_free": 10.0})
    assert res.approved
    assert res.lot_size == 0.05
