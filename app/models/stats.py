import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LifetimeStats(Base):
    __tablename__ = "lifetime_stats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    total_runs_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_days_qualified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_gas_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_crashes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_corner_saves: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_weather_survived: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_ghost_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_lootboxes_opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cars_owned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
