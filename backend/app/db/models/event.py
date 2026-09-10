from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LiquiditySweepEventModel(Base):
    __tablename__ = "liquidity_sweep_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    liquidity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    level_price: Mapped[float] = mapped_column(Float, nullable=False)
    sweep_price: Mapped[float] = mapped_column(Float, nullable=False)
    detected_via: Mapped[str] = mapped_column(String(20), default="candle", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_event_symbol_occurred", "symbol", "occurred_at"),
    )
