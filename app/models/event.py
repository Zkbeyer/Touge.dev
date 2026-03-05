import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyRunEvents(Base):
    __tablename__ = "daily_run_events"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_run_events_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Rolls
    corner_roll: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_roll: Mapped[float | None] = mapped_column(Float, nullable=True)
    ghost_roll: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Corner event
    corner_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    corner_requirement: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    corner_time_save_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Weather event
    weather_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    weather_requirement: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    weather_penalty_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Ghost event
    ghost_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ghost_difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ghost_requirement: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Outcomes
    corner_completed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    weather_survived: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ghost_won: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DailyProcessedDay(Base):
    __tablename__ = "daily_processed_days"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_processed_days_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=True
    )
    qualified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    gas_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    crashed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    segment_advanced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    run_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stopwatch_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
