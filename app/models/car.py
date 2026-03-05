import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Perk(Base):
    __tablename__ = "perks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    effect_type: Mapped[str] = mapped_column(String(128), nullable=False)
    effect_value: Mapped[float] = mapped_column(Float, nullable=False)


class CarCatalog(Base):
    __tablename__ = "car_catalog"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    rarity: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    base_model: Mapped[str] = mapped_column(String(255), nullable=False)
    max_upgrade_level: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    perk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("perks.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CarOwnership(Base):
    __tablename__ = "car_ownership"
    __table_args__ = (UniqueConstraint("user_id", "car_catalog_id", name="uq_car_ownership_user_car"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    car_catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("car_catalog.id"), nullable=False
    )
    upgrade_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    iconic_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    perk_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    obtained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
