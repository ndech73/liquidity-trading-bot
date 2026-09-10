from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketSnapshotModel(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), default="5m", nullable=False)
    candles_analyzed: Mapped[int] = mapped_column(Integer, nullable=False)
    atr: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_regime: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_compressed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_expanded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_snapshot_symbol_recorded", "symbol", "recorded_at"),
    )
