from datetime import datetime

from pydantic import BaseModel


class PerkInfo(BaseModel):
    id: str
    slug: str
    name: str
    description: str
    effect_type: str
    effect_value: float


class CarCatalogInfo(BaseModel):
    id: str
    name: str
    slug: str
    rarity: str
    description: str
    base_model: str
    max_upgrade_level: int
    perk: PerkInfo | None


class OwnedCarResponse(BaseModel):
    id: str  # ownership id
    car: CarCatalogInfo
    upgrade_level: int
    iconic_unlocked: bool
    perk_active: bool
    obtained_at: datetime

    @property
    def upgrade_cost_next(self) -> int | None:
        from app.services.garage import RARITY_MULTIPLIERS, UPGRADE_BASE_COSTS
        if self.upgrade_level >= self.car.max_upgrade_level:
            return None
        base = UPGRADE_BASE_COSTS[self.upgrade_level]
        multiplier = RARITY_MULTIPLIERS.get(self.car.rarity, 1.0)
        return int(base * multiplier)


class UpgradeResponse(BaseModel):
    upgrade_level: int
    max_upgrade_level: int
    iconic_unlocked: bool
    cost_paid: int


class CosmeticResponse(BaseModel):
    id: str
    slug: str
    name: str
    type: str
    rarity: str
    source_description: str
    obtained_at: datetime
