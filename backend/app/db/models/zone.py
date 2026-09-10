from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LiquidityZoneModel(Base):
    __tablename__ = "liquidity_zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    liquidity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    touches: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    swept_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sweep_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_zone_symbol_status", "symbol", "status"),
        Index("ix_zone_symbol_side", "symbol", "side"),
    )
