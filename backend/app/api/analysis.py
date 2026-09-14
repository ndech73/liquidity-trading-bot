from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.zone import LiquidityZoneModel
from app.db.models.event import LiquiditySweepEventModel
from app.analysis_engine.domain.candle import Timeframe

router = APIRouter()


TF_MAP = {
    "1m": Timeframe.M1, "m1": Timeframe.M1,
    "5m": Timeframe.M5, "m5": Timeframe.M5,
    "15m": Timeframe.M15, "m15": Timeframe.M15,
    "30m": Timeframe.M30, "m30": Timeframe.M30,
    "1h": Timeframe.H1, "h1": Timeframe.H1,
    "4h": Timeframe.H4, "h4": Timeframe.H4,
    "1d": Timeframe.D1, "d1": Timeframe.D1,
}


@router.get("/analysis/zones")
def get_zones(
    symbol: str = Query("EURJPY"),
    timeframe: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Returns detected structural liquidity levels for a symbol and timeframe."""
    sym = symbol.upper()
    tf_str = (timeframe or "15m").lower()
    norm_tf = TF_MAP.get(tf_str, Timeframe.M15)
    tf_val = norm_tf.value

    # 1. Primary: Run live analysis on actual timeframe candles from MT5 if available
    try:
        from app.execution.mt5_executor import MT5Executor
        from app.analysis_engine.engine import AnalysisEngine
        executor = MT5Executor()
        if executor.connect():
            candles = executor.fetch_candles(sym, norm_tf, 120)
            if candles and len(candles) >= 20:
                engine = AnalysisEngine()
                snap = engine.analyze(candles)
                executor.close()

                detected = []
                for z in snap.zones:
                    origin_ts = int(z.created_at.timestamp()) if hasattr(z.created_at, "timestamp") else 0
                    sweep_ts = int(z.swept_at.timestamp()) if z.swept_at and hasattr(z.swept_at, "timestamp") else None
                    is_swept = str(getattr(z.status, "value", z.status)).lower() == "swept"
                    detected.append({
                        "id": f"{sym}_{tf_val}_{getattr(z.side, 'value', str(z.side)).lower()}_{round(z.price, 5)}_{origin_ts}",
                        "symbol": sym,
                        "timeframe": tf_val,
                        "price": round(z.price, 5),
                        "priceHigh": round(z.price * 1.0002, 5),
                        "priceLow": round(z.price * 0.9998, 5),
                        "type": "BUY_SIDE" if (getattr(z.side, "value", str(z.side)).lower() == "buyside") else "SELL_SIDE",
                        "liquidityType": z.liquidity_type.value if hasattr(z.liquidity_type, "value") else str(z.liquidity_type),
                        "status": "SWEPT" if is_swept else "ACTIVE",
                        "strength": round(min(1.0, 0.5 + (z.touches * 0.15)), 2),
                        "isSwept": is_swept,
                        "touches": z.touches,
                        "originTime": origin_ts,
                        "createdAt": z.created_at.isoformat() if hasattr(z.created_at, "isoformat") else str(z.created_at),
                        "sweepTime": sweep_ts,
                        "sweptAt": z.swept_at.isoformat() if z.swept_at and hasattr(z.swept_at, "isoformat") else None,
                        "sweepPrice": round(z.sweep_price, 5) if z.sweep_price else None,
                    })
                return detected
            executor.close()
    except Exception:
        pass

    # 2. Fallback: Query database for cached zones on the requested symbol and timeframe
    try:
        query = db.query(LiquidityZoneModel).filter_by(symbol=sym, timeframe=tf_val)
        zones = query.order_by(LiquidityZoneModel.created_at.desc()).limit(50).all()
    except Exception:
        zones = []

    res = []
    seen_levels = set()
    for z in zones:
        origin_ts = int(z.created_at.timestamp()) if hasattr(z.created_at, "timestamp") else 0
        sweep_ts = int(z.swept_at.timestamp()) if getattr(z, "swept_at", None) and hasattr(z.swept_at, "timestamp") else None
        is_swept = z.status.lower() == "swept"
        key = (round(z.price, 4), z.side.lower(), origin_ts)
        if key in seen_levels:
            continue
        seen_levels.add(key)
        res.append({
            "id": f"{sym}_{tf_val}_{z.side.lower()}_{round(z.price, 5)}_{origin_ts}",
            "symbol": sym,
            "timeframe": z.timeframe,
            "price": round(z.price, 5),
            "priceHigh": round(z.price * 1.0002, 5),
            "priceLow": round(z.price * 0.9998, 5),
            "type": "BUY_SIDE" if z.side.lower() == "buyside" else "SELL_SIDE",
            "liquidityType": getattr(z, "liquidity_type", "swing_point"),
            "status": "SWEPT" if is_swept else "ACTIVE",
            "strength": round(min(1.0, 0.5 + (z.touches * 0.15)), 2),
            "isSwept": is_swept,
            "touches": z.touches,
            "originTime": origin_ts,
            "createdAt": z.created_at.isoformat() if hasattr(z.created_at, "isoformat") else str(z.created_at),
            "sweepTime": sweep_ts,
            "sweptAt": z.swept_at.isoformat() if getattr(z, "swept_at", None) and hasattr(z.swept_at, "isoformat") else None,
            "sweepPrice": round(z.sweep_price, 5) if getattr(z, "sweep_price", None) else None,
        })
    return res


@router.get("/analysis/sweeps")
def get_sweeps(
    symbol: str = Query("EURJPY"),
    timeframe: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Returns liquidity sweep breach events for a symbol and timeframe."""
    sym = symbol.upper()
    tf_str = (timeframe or "15m").lower()
    norm_tf = TF_MAP.get(tf_str, Timeframe.M15)
    tf_val = norm_tf.value

    try:
        query = db.query(LiquiditySweepEventModel).filter_by(symbol=sym, timeframe=tf_val)
        sweeps = query.order_by(LiquiditySweepEventModel.occurred_at.desc()).limit(50).all()
    except Exception:
        sweeps = []

    if not sweeps:
        try:
            from app.execution.mt5_executor import MT5Executor
            from app.analysis_engine.engine import AnalysisEngine

            executor = MT5Executor()
            if executor.connect():
                candles = executor.fetch_candles(sym, norm_tf, 120)
                if candles and len(candles) >= 20:
                    engine = AnalysisEngine()
                    snap = engine.analyze(candles)
                    detected_sweeps = []
                    for s in snap.sweep_events:
                        detected_sweeps.append({
                            "id": s.id,
                            "symbol": s.symbol,
                            "timeframe": tf_val,
                            "timestamp": s.occurred_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(s.occurred_at, "strftime") else str(s.occurred_at),
                            "price": round(s.sweep_price, 5),
                            "sweepType": "HIGH_SWEEP" if getattr(s.side, "value", str(s.side)).lower() == "buyside" else "LOW_SWEEP",
                            "reactionMagnitudePips": round(abs(s.sweep_price - s.level_price) * 10000, 1),
                        })
                    executor.close()
                    return detected_sweeps
                executor.close()
        except Exception:
            pass

    return [
        {
            "id": s.id,
            "symbol": s.symbol,
            "timeframe": s.timeframe,
            "timestamp": s.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
            "price": round(s.sweep_price, 5),
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
def get_analysis_status(symbol: str = Query("EURJPY"), db: Session = Depends(get_db)):
    """Returns market structure, compression, expansion and regime state for a symbol across M15 and H1."""
    from app.db.models.snapshot import MarketSnapshotModel
    from app.execution.mt5_executor import MT5Executor
    from app.analysis_engine.domain.candle import Timeframe
    from app.analysis_engine.engine import AnalysisEngine

    snap_m15 = (
        db.query(MarketSnapshotModel)
        .filter_by(symbol=symbol.upper(), timeframe="15m")
        .order_by(MarketSnapshotModel.recorded_at.desc())
        .first()
    )
    snap_h1 = (
        db.query(MarketSnapshotModel)
        .filter_by(symbol=symbol.upper(), timeframe="1h")
        .order_by(MarketSnapshotModel.recorded_at.desc())
        .first()
    )

    # Fallback to any snapshot if 15m not yet recorded
    primary_snap = snap_m15 or snap_h1 or (
        db.query(MarketSnapshotModel)
        .filter_by(symbol=symbol.upper())
        .order_by(MarketSnapshotModel.recorded_at.desc())
        .first()
    )

    if primary_snap:
        htf_structure = "BULLISH" if (snap_h1 and snap_h1.is_expanded) else "RANGING"
        return {
            "symbol": symbol.upper(),
            "hasData": True,
            "regime": (primary_snap.volatility_regime or "NORMAL").upper(),
            "atr": round(primary_snap.atr, 5) if primary_snap.atr else None,
            "compressionRatio": 0.65 if primary_snap.is_compressed else 1.0,
            "isCompressed": primary_snap.is_compressed,
            "expansionRatio": 1.5 if primary_snap.is_expanded else 1.0,
            "isExpanded": primary_snap.is_expanded,
            "higherTimeframeStructure": htf_structure,
            "executionTimeframeStructure": "EXPANDING" if primary_snap.is_expanded else "CONSOLIDATING",
            "lastStructureBreak": primary_snap.recorded_at.strftime("%Y-%m-%d %H:%M:%S") if primary_snap.recorded_at else None,
        }

    try:
        executor = MT5Executor()
        if executor.connect():
            candles = executor.fetch_candles(symbol.upper(), Timeframe.M15, 120)
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

