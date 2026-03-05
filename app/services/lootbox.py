import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.car import CarCatalog, CarOwnership
from app.models.reward import Lootbox
from app.models.stats import LifetimeStats
from app.models.user import User
from app.services.events import _roll

TIER_THRESHOLDS = [
    ("platinum", 120),
    ("gold", 80),
    ("silver", 50),
    ("bronze", 0),
]

TIER_DROP_RATES: dict[str, dict[str, float]] = {
    "bronze":   {"common": 0.80, "rare": 0.18, "epic": 0.018, "legendary": 0.002},
    "silver":   {"common": 0.60, "rare": 0.30, "epic": 0.09,  "legendary": 0.01},
    "gold":     {"common": 0.30, "rare": 0.45, "epic": 0.20,  "legendary": 0.05},
    "platinum": {"common": 0.10, "rare": 0.40, "epic": 0.35,  "legendary": 0.15},
}

DUPE_POINTS = {"common": 50, "rare": 150, "epic": 400, "legendary": 1000}


def pick_lootbox_tier(score: int) -> str:
    for tier, threshold in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "bronze"


def _weighted_pick(rates: dict[str, float], roll: float) -> str:
    cumulative = 0.0
    for rarity, weight in rates.items():
        cumulative += weight
        if roll < cumulative:
            return rarity
    return list(rates.keys())[-1]


async def open_lootbox(lootbox_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    Opens a lootbox, awards a car or points (if duplicate).
    Returns a result dict with what was awarded.
    """
    lootbox = await db.get(Lootbox, lootbox_id, with_for_update=True)
    if not lootbox or lootbox.user_id != user_id:
        raise ValueError("Lootbox not found")
    if lootbox.opened:
        raise ValueError("Lootbox already opened")

    user = await db.get(User, user_id, with_for_update=True)

    rates = TIER_DROP_RATES[lootbox.tier]
    today = datetime.now(timezone.utc).date()

    # Deterministic rarity roll
    rarity_roll = _roll(lootbox_id, today, "open_rarity")
    rarity = _weighted_pick(rates, rarity_roll)

    # Get cars of this rarity
    cars = (await db.scalars(
        select(CarCatalog).where(CarCatalog.rarity == rarity, CarCatalog.is_active == True)
    )).all()

    result: dict = {"rarity": rarity}

    if not cars:
        # Fallback: give points
        points = DUPE_POINTS.get(rarity, 50)
        user.total_points += points
        user.spendable_points += points
        lootbox.points_awarded = points
        result["type"] = "points"
        result["points"] = points
    else:
        # Pick a car deterministically
        car_roll = _roll(lootbox_id, today, "open_car")
        car = cars[int(car_roll * len(cars)) % len(cars)]

        owned = await db.scalar(
            select(CarOwnership).where(
                CarOwnership.user_id == user_id,
                CarOwnership.car_catalog_id == car.id,
            )
        )

        if owned:
            # Duplicate — convert to points
            points = DUPE_POINTS[rarity]
            user.total_points += points
            user.spendable_points += points
            lootbox.points_awarded = points
            result["type"] = "duplicate_points"
            result["car_name"] = car.name
            result["points"] = points
        else:
            db.add(CarOwnership(
                user_id=user_id,
                car_catalog_id=car.id,
                obtained_at=datetime.now(timezone.utc),
            ))
            lootbox.car_awarded_id = car.id
            result["type"] = "car"
            result["car_id"] = str(car.id)
            result["car_name"] = car.name

            # Update lifetime stats
            stats = await db.get(LifetimeStats, user_id)
            if stats:
                stats.total_cars_owned += 1

    lootbox.opened = True
    lootbox.opened_at = datetime.now(timezone.utc)
    # Update lifetime stats
    stats = await db.get(LifetimeStats, user_id)
    if stats:
        stats.total_lootboxes_opened += 1

    await db.commit()
    return result
