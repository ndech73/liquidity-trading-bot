"""Tests for app.analysis_engine.engine."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from app.analysis_engine.domain.candle import Candle, Timeframe
from app.analysis_engine.domain.liquidity import (
    LiquiditySide,
    LiquidityStatus,
    LiquidityType,
    LiquidityZone,
)
from app.analysis_engine.engine import AnalysisEngine, MarketSnapshot
from app.analysis_engine.volatility.analyzer import VolatilityReading

START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_series(n: int, symbol: str = "EURUSD", base: float = 1.1000) -> list[Candle]:
    """A deterministic but varied candle series, long enough to exercise
    liquidity, volatility, compression, and expansion all at once with
    default thresholds (needs at least 25 candles for compression and
    expansion, whose default windows are recent=5 + baseline=20)."""
    candles = []
    price = base
    for i in range(n):
        drift = 0.0002 if i % 3 == 0 else -0.0001
        open_ = price
        close = price + drift
        high = max(open_, close) + 0.0003 + 0.0001 * (i % 4)
        low = min(open_, close) - 0.0002 - 0.0001 * ((i + 2) % 3)
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=Timeframe.M1,
                timestamp=START + timedelta(minutes=i),
                open=open_,
                high=high,
                low=low,
                close=close,
            )
        )
        price = close
    return candles


class FakeContextBuilder:
    """A stand-in for the future context/builder.py, so engine.py's
    optional-context-builder slot can be tested before that file
    exists."""

    def __init__(self, result: object = "FAKE_CONTEXT") -> None:
        self.result = result
        self.received_snapshot: MarketSnapshot | None = None

    def build(self, snapshot: MarketSnapshot) -> object:
        self.received_snapshot = snapshot
        return self.result


class TestAnalyzeBasics:
    def test_raises_on_empty_candles(self) -> None:
        engine = AnalysisEngine()
        with pytest.raises(ValueError):
            engine.analyze([])

    def test_snapshot_reports_symbol_and_candle_count(self) -> None:
        engine = AnalysisEngine()
        candles = make_series(40)

        snapshot = engine.analyze(candles)

        assert snapshot.symbol == candles[-1].symbol
        assert snapshot.candles_analyzed == 40
        assert isinstance(snapshot.zones, list)
        assert isinstance(snapshot.sweep_events, list)


class TestAnalyzePopulatesSubReadings:
    def test_enough_candles_populates_all_readings(self) -> None:
        engine = AnalysisEngine()
        candles = make_series(40)  # enough for volatility(15) + compression/expansion(25)

        snapshot = engine.analyze(candles)

        assert isinstance(snapshot.volatility, VolatilityReading)
        assert snapshot.compression is not None
        assert snapshot.expansion is not None

    def test_too_few_candles_leaves_readings_none(self) -> None:
        engine = AnalysisEngine()
        candles = make_series(5)  # well under every module's minimum

        snapshot = engine.analyze(candles)

        assert snapshot.volatility is None
        assert snapshot.compression is None
        assert snapshot.expansion is None


class TestZoneMergingAcrossRuns:
    def test_rerunning_same_candles_does_not_duplicate_zones(self) -> None:
        engine = AnalysisEngine()
        candles = make_series(40)

        first = engine.analyze(candles)
        second = engine.analyze(candles, existing_zones=first.zones)

        assert len(second.zones) == len(first.zones)

    def test_merge_zones_skips_duplicate_when_existing_zone_active(self) -> None:
        engine = AnalysisEngine()
        existing = LiquidityZone(
            symbol="EURUSD",
            timeframe=Timeframe.M1,
            side=LiquiditySide.BUYSIDE,
            liquidity_type=LiquidityType.SWING_HIGH,
            price=1.1050,
            created_at=START,
        )
        newly_detected = LiquidityZone(
            symbol="EURUSD",
            timeframe=Timeframe.M1,
            side=LiquiditySide.BUYSIDE,
            liquidity_type=LiquidityType.SWING_HIGH,
            price=1.1050,
            created_at=START + timedelta(minutes=5),
        )

        merged = engine._merge_zones([existing], [newly_detected])

        assert merged == [existing]

    def test_merge_zones_keeps_swept_zone_and_adds_new_active_one(self) -> None:
        engine = AnalysisEngine()
        swept = LiquidityZone(
            symbol="EURUSD",
            timeframe=Timeframe.M1,
            side=LiquiditySide.BUYSIDE,
            liquidity_type=LiquidityType.SWING_HIGH,
            price=1.1050,
            created_at=START,
            status=LiquidityStatus.SWEPT,
            swept_at=START + timedelta(minutes=1),
            sweep_price=1.1055,
        )
        newly_detected = LiquidityZone(
            symbol="EURUSD",
            timeframe=Timeframe.M1,
            side=LiquiditySide.BUYSIDE,
            liquidity_type=LiquidityType.SWING_HIGH,
            price=1.1050,
            created_at=START + timedelta(minutes=10),
        )

        merged = engine._merge_zones([swept], [newly_detected])

        assert len(merged) == 2
        assert merged[0] is swept
        assert merged[0].status == LiquidityStatus.SWEPT  # untouched
        assert merged[1] is newly_detected
        assert merged[1].status == LiquidityStatus.ACTIVE


class TestContextBuilderIntegration:
    def test_context_stays_none_without_a_builder(self) -> None:
        engine = AnalysisEngine()
        candles = make_series(10)

        snapshot = engine.analyze(candles)

        assert snapshot.context is None

    def test_context_builder_receives_snapshot_and_result_is_attached(self) -> None:
        fake_builder = FakeContextBuilder(result={"trend": "up"})
        engine = AnalysisEngine(context_builder=fake_builder)
        candles = make_series(10)

        snapshot = engine.analyze(candles)

        assert snapshot.context == {"trend": "up"}
        assert fake_builder.received_snapshot is not None
        assert fake_builder.received_snapshot.symbol == snapshot.symbol