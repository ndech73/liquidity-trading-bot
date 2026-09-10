from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.zone import LiquidityZoneModel
from app.db.models.event import LiquiditySweepEventModel

router = APIRouter()


@router.get("/analysis/zones")
def get_zones(symbol: str = Query("EURUSD"), db: Session = Depends(get_db)):
    """Returns detected liquidity zones for a symbol from database."""
    zones = db.query(LiquidityZoneModel).filter_by(symbol=symbol.upper()).order_by(LiquidityZoneModel.created_at.desc()).limit(50).all()

    return [
        {
            "id": z.id,
            "symbol": z.symbol,
            "timeframe": z.timeframe,
            "priceHigh": round(z.price * 1.0002, 5),
            "priceLow": round(z.price * 0.9998, 5),
            "type": "BUY_SIDE" if z.side.lower() == "buyside" else "SELL_SIDE",
            "strength": round(min(1.0, 0.5 + (z.touches * 0.15)), 2),
            "isSwept": z.status.lower() == "swept",
            "touches": z.touches,
            "createdAt": z.created_at.isoformat(),
        }
        for z in zones
    ]


@router.get("/analysis/sweeps")
def get_sweeps(symbol: str = Query("EURUSD"), db: Session = Depends(get_db)):
    """Returns liquidity sweep breach events for a symbol from database."""
    sweeps = db.query(LiquiditySweepEventModel).filter_by(symbol=symbol.upper()).order_by(LiquiditySweepEventModel.occurred_at.desc()).limit(50).all()

    return [
        {
            "id": s.id,
            "symbol": s.symbol,
            "timestamp": s.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
            "price": s.sweep_price,
            "sweepType": "HIGH_SWEEP" if s.side.lower() == "buyside" else "LOW_SWEEP",
            "reactionMagnitudePips": round(abs(s.sweep_price - s.level_price) * 10000, 1),
        }
        for s in sweeps
    ]


@router.get("/analysis/overview")
def get_analysis_overview(db: Session = Depends(get_db)):
    """Returns liquidity and volatility summary counts across all symbols."""
    total_zones = db.query(LiquidityZoneModel).count()
    active_zones = db.query(LiquidityZoneModel).filter_by(status="active").count()
    total_sweeps = db.query(LiquiditySweepEventModel).count()

    return {
        "total_zones": total_zones,
        "active_zones": active_zones,
        "swept_zones": total_zones - active_zones,
        "total_sweeps": total_sweeps,
    }


@router.get("/analysis/status")
def get_analysis_status(symbol: str = Query("EURUSD"), db: Session = Depends(get_db)):
    """Returns market structure, compression, expansion and regime state for a symbol."""
    from app.db.models.snapshot import MarketSnapshotModel
    from app.execution.mt5_executor import MT5Executor
    from app.analysis_engine.domain.candle import Timeframe
    from app.analysis_engine.engine import AnalysisEngine

    snapshot_model = (
        db.query(MarketSnapshotModel)
        .filter_by(symbol=symbol.upper())
        .order_by(MarketSnapshotModel.recorded_at.desc())
        .first()
    )

    if snapshot_model:
        return {
            "symbol": symbol.upper(),
            "hasData": True,
            "regime": (snapshot_model.volatility_regime or "NORMAL").upper(),
            "atr": round(snapshot_model.atr, 5) if snapshot_model.atr else None,
            "compressionRatio": 0.65 if snapshot_model.is_compressed else 1.0,
            "isCompressed": snapshot_model.is_compressed,
            "expansionRatio": 1.5 if snapshot_model.is_expanded else 1.0,
            "isExpanded": snapshot_model.is_expanded,
            "higherTimeframeStructure": "BULLISH" if snapshot_model.is_expanded else "RANGING",
            "executionTimeframeStructure": "EXPANDING" if snapshot_model.is_expanded else "CONSOLIDATING",
            "lastStructureBreak": snapshot_model.recorded_at.strftime("%Y-%m-%d %H:%M:%S") if snapshot_model.recorded_at else None,
        }

    try:
        executor = MT5Executor()
        if executor.connect():
            candles = executor.fetch_candles(symbol.upper(), Timeframe.M5, 120)
            if candles and len(candles) >= 30:
                engine = AnalysisEngine()
                snap = engine.analyze(candles)
                executor.close()
                return {
                    "symbol": symbol.upper(),
                    "hasData": True,
                    "regime": snap.volatility.regime.value.upper() if snap.volatility else "NORMAL",
                    "atr": round(snap.volatility.atr, 5) if snap.volatility else None,
                    "compressionRatio": round(snap.compression.contraction_ratio, 2) if snap.compression else None,
                    "isCompressed": snap.compression.is_compressed if snap.compression else False,
                    "expansionRatio": round(snap.expansion.expansion_ratio, 2) if snap.expansion else None,
                    "isExpanded": snap.expansion.is_expanding if snap.expansion else False,
                    "higherTimeframeStructure": "BULLISH" if (candles[-1].close >= candles[0].close) else "BEARISH",
                    "executionTimeframeStructure": "EXPANDING" if (snap.expansion and snap.expansion.is_expanding) else "CONSOLIDATING",
                    "lastStructureBreak": candles[-1].timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(candles[-1].timestamp, "strftime") else str(candles[-1].timestamp),
                }
            executor.close()
    except Exception:
        pass

    return {
        "symbol": symbol.upper(),
        "hasData": False,
        "regime": None,
        "atr": None,
        "compressionRatio": None,
        "isCompressed": False,
        "expansionRatio": None,
        "isExpanded": False,
        "higherTimeframeStructure": None,
        "executionTimeframeStructure": None,
        "lastStructureBreak": None,
    }

