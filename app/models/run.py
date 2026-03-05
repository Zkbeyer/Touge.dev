import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Run(Base):
    __tablename__ = "runs"
    # Partial unique index enforced at DB level (PostgreSQL: WHERE is_complete = FALSE).
    # Application logic also enforces one active run per user.
    __table_args__ = (
        Index("ix_runs_user_active", "user_id", "is_complete"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_processed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    stopwatch_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    corner_saves: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weather_penalties_taken: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ghost_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lootbox_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # For momentum perk: absorb 1 crash at 10+ streak (once per run)
    momentum_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CompletedRun(Base):
    __tablename__ = "completed_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    corner_saves: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weather_penalties_taken: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ghost_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    streak_at_completion: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lootbox_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gas_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pb_set: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
