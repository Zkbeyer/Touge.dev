import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Cosmetic(Base):
    __tablename__ = "cosmetics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    rarity: Mapped[str] = mapped_column(String(32), nullable=False)
    source_description: Mapped[str] = mapped_column(String(512), nullable=False, default="")


class CosmeticInventory(Base):
    __tablename__ = "cosmetic_inventory"
    __table_args__ = (UniqueConstraint("user_id", "cosmetic_id", name="uq_cosmetic_inventory_user_cosmetic"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    cosmetic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cosmetics.id"), nullable=False
    )
    obtained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
