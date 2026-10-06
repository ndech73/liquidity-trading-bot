from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.db.init_db import init_db
from app.db.session import check_db_connection
from app.api.account import router as account_router
from app.api.dashboard import router as dashboard_router
from app.api.markets import router as markets_router
from app.api.trades import router as trades_router
from app.api.analysis import router as analysis_router
from app.api.forensics import router as forensics_router
import asyncio
from app.api.performance import router as performance_router
from app.api.settings import router as settings_router
from app.api.notifications import router as notifications_router
from app.api.websocket import router as ws_router, ws_relay_worker
from app.strategy.trading_runner import trading_bot_worker, trading_runner


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting Liquidity Trading System backend...")
    db_status = check_db_connection()
    if db_status.get("connected"):
        logger.success("Database connected. Initializing tables...")
        init_db()
    else:
        logger.warning(f"Database connection unavailable at startup: {db_status.get('error')}")

    relay_task = asyncio.create_task(ws_relay_worker())
    bot_task = asyncio.create_task(trading_bot_worker())

    yield

    logger.info("Shutting down Liquidity Trading System backend...")
    trading_runner.stop()
    bot_task.cancel()
    relay_task.cancel()
    try:
        await asyncio.gather(bot_task, relay_task, return_exceptions=True)
    except Exception:
        pass
    from app.execution.mt5_executor import MT5Executor
    MT5Executor.force_disconnect()



app = FastAPI(
    title="Liquidity Trading System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(account_router, prefix="/api", tags=["account"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(markets_router, prefix="/api", tags=["markets"])
app.include_router(trades_router, prefix="/api", tags=["trades"])
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
app.include_router(forensics_router, prefix="/api", tags=["forensics"])
app.include_router(performance_router, prefix="/api", tags=["performance"])
app.include_router(settings_router, prefix="/api", tags=["settings"])
app.include_router(notifications_router, prefix="/api", tags=["notifications"])
app.include_router(ws_router, tags=["websocket"])


@app.get("/api/health")
def health() -> dict[str, object]:
    db_status = check_db_connection()
    return {
        "status": "ok",
        "service": "liquidity-trading-system",
        "database": db_status,
    }


@app.get("/api/health/db")
def health_db() -> dict[str, object]:
    return check_db_connection()


