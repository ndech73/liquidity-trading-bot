from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.init_db import init_db
from app.db.models import (
    LiquiditySweepEventModel,
    LiquidityZoneModel,
    MarketSnapshotModel,
    TradeModel,
)
from app.db.session import SessionLocal, check_db_connection, engine
from app.main import app


def test_db_connection_check():
    status = check_db_connection()
    assert status["connected"] is True
    assert status["database"] == "postgresql"
    assert "PostgreSQL" in str(status["version"])


def test_db_init_creates_tables():
    assert init_db() is True
    table_names = list(Base.metadata.tables.keys())
    assert "liquidity_zones" in table_names
    assert "liquidity_sweep_events" in table_names
    assert "trades" in table_names
    assert "market_snapshots" in table_names


def test_crud_liquidity_zone():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        zone = LiquidityZoneModel(
            symbol="EURUSD",
            timeframe="15m",
            side="buyside",
            liquidity_type="swing_high",
            price=1.1050,
            status="active",
            touches=1,
            created_at=now,
        )
        db.add(zone)
        db.commit()
        db.refresh(zone)

        assert zone.id is not None
        assert zone.symbol == "EURUSD"
        assert zone.price == 1.1050

        # Query back
        found = db.query(LiquidityZoneModel).filter_by(id=zone.id).first()
        assert found is not None
        assert found.price == 1.1050

        # Clean up
        db.delete(found)
        db.commit()
    finally:
        db.close()


def test_crud_trade():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        trade = TradeModel(
            ticket=9999991,
            symbol="GBPUSD",
            order_type="BUY",
            lots=0.10,
            open_price=1.2750,
            stop_loss=1.2700,
            take_profit=1.2850,
            profit=45.20,
            status="OPEN",
            opened_at=now,
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)

        assert trade.ticket == 9999991
        assert trade.symbol == "GBPUSD"

        # Query back
        retrieved = db.query(TradeModel).filter_by(ticket=9999991).first()
        assert retrieved is not None
        assert retrieved.lots == 0.10

        # Clean up
        db.delete(retrieved)
        db.commit()
    finally:
        db.close()


def test_health_endpoints():
    client = TestClient(app)

    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["database"]["connected"] is True

    res_db = client.get("/api/health/db")
    assert res_db.status_code == 200
    assert res_db.json()["connected"] is True
