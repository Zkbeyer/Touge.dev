import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.car import CarCatalog, CarOwnership, Perk
from app.models.user import User

# Upgrade cost per level (level 0->1 is index 0, 4->5 is index 4)
UPGRADE_BASE_COSTS = [100, 200, 350, 500, 750]

RARITY_MULTIPLIERS = {
    "common": 1.0,
    "rare": 1.5,
    "epic": 2.5,
    "legendary": 4.0,
}


def _upgrade_cost(current_level: int, rarity: str) -> int:
    if current_level >= len(UPGRADE_BASE_COSTS):
        raise ValueError("Already at max level")
    base = UPGRADE_BASE_COSTS[current_level]
    multiplier = RARITY_MULTIPLIERS.get(rarity, 1.0)
    return int(base * multiplier)


async def user_has_active_perk(user_id: uuid.UUID, perk_slug: str, db: AsyncSession) -> bool:
    """Returns True if user owns a car with the given perk active."""
    result = await db.execute(
        select(CarOwnership)
        .join(CarCatalog, CarOwnership.car_catalog_id == CarCatalog.id)
        .join(Perk, CarCatalog.perk_id == Perk.id)
        .where(
            CarOwnership.user_id == user_id,
            CarOwnership.perk_active == True,
            Perk.slug == perk_slug,
        )
    )
    return result.scalar() is not None


async def upgrade_car(
    user_id: uuid.UUID, car_ownership_id: uuid.UUID, db: AsyncSession
) -> dict:
    """
    Upgrades a car one level. Returns updated ownership info.
    Raises ValueError if insufficient points or already at max.
    """
    ownership = await db.get(CarOwnership, car_ownership_id, with_for_update=True)
    if not ownership or ownership.user_id != user_id:
        raise ValueError("Car not found in garage")

    car = await db.get(CarCatalog, ownership.car_catalog_id)
    user = await db.get(User, user_id, with_for_update=True)

    if ownership.upgrade_level >= car.max_upgrade_level:
        raise ValueError("Car already at maximum upgrade level")

    cost = _upgrade_cost(ownership.upgrade_level, car.rarity)
    if user.spendable_points < cost:
        raise ValueError(f"Insufficient points. Need {cost}, have {user.spendable_points}")

    user.spendable_points -= cost
    ownership.upgrade_level += 1

    # Check if max level reached
    if ownership.upgrade_level >= car.max_upgrade_level:
        ownership.iconic_unlocked = True

    await db.commit()
    return {
        "upgrade_level": ownership.upgrade_level,
        "max_upgrade_level": car.max_upgrade_level,
        "iconic_unlocked": ownership.iconic_unlocked,
        "cost_paid": cost,
    }


async def select_car(user_id: uuid.UUID, car_ownership_id: uuid.UUID, db: AsyncSession) -> None:
    """Sets a car as the user's active car."""
    ownership = await db.get(CarOwnership, car_ownership_id)
    if not ownership or ownership.user_id != user_id:
        raise ValueError("Car not found in garage")

    user = await db.get(User, user_id, with_for_update=True)
    user.active_car_id = ownership.car_catalog_id
    await db.commit()


async def toggle_perk(
    user_id: uuid.UUID, car_ownership_id: uuid.UUID, active: bool, db: AsyncSession
) -> None:
    """Toggles perk activation on a car. Perk must be unlocked (iconic)."""
    ownership = await db.get(CarOwnership, car_ownership_id, with_for_update=True)
    if not ownership or ownership.user_id != user_id:
        raise ValueError("Car not found in garage")
    if not ownership.iconic_unlocked:
        raise ValueError("Perk not yet unlocked — reach max upgrade level first")

    ownership.perk_active = active
    await db.commit()
