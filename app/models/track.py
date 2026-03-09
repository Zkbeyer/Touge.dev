import uuid

from sqlalchemy import Boolean, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    length_days: Mapped[int] = mapped_column(Integer, nullable=False)
    base_seconds_per_segment: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Predefined segment layout: list of {"type": "straight"|"sweeper"|"chicane"|"hairpin", "name": str}
    # Length must match length_days. If None, all segments treated as straights (no corner events).
    segment_layout: Mapped[list | None] = mapped_column(JSON, nullable=True)
