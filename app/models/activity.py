import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyActivity(Base):
    __tablename__ = "daily_activity"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_activity_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    github_commit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lc_easy_accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lc_medium_accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lc_hard_accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lc_total_accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_finalized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
