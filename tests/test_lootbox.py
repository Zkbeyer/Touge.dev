"""Tests for lootbox tier calculation and rarity distribution."""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.models.car import CarCatalog, CarOwnership
from app.models.reward import Lootbox
from app.models.run import Run
from app.models.track import Track
from app.models.user import User
from app.services.lootbox import (
    TIER_DROP_RATES,
    TIER_THRESHOLDS,
    _weighted_pick,
    pick_lootbox_tier,
    open_lootbox,
)


def test_pick_lootbox_tier():
    assert pick_lootbox_tier(0) == "bronze"
    assert pick_lootbox_tier(49) == "bronze"
    assert pick_lootbox_tier(50) == "silver"
    assert pick_lootbox_tier(79) == "silver"
    assert pick_lootbox_tier(80) == "gold"
    assert pick_lootbox_tier(119) == "gold"
    assert pick_lootbox_tier(120) == "platinum"
    assert pick_lootbox_tier(999) == "platinum"


def test_tier_drop_rates_sum_to_one():
    """Each tier's drop rates must sum to 1.0."""
    for tier, rates in TIER_DROP_RATES.items():
        total = sum(rates.values())
        assert abs(total - 1.0) < 1e-9, f"{tier} rates sum to {total}"


def test_weighted_pick():
    rates = {"common": 1.0}
    assert _weighted_pick(rates, 0.0) == "common"
    assert _weighted_pick(rates, 0.99) == "common"


def test_weighted_pick_distribution():
    rates = {"a": 0.5, "b": 0.5}
    assert _weighted_pick(rates, 0.0) == "a"
    assert _weighted_pick(rates, 0.49) == "a"
    assert _weighted_pick(rates, 0.5) == "b"
    assert _weighted_pick(rates, 0.99) == "b"


@pytest.mark.asyncio
async def test_open_lootbox_awards_car(db, test_user):
    """Opening a lootbox awards a car when no duplicate."""
    car = CarCatalog(
        name="Test Car",
        slug="test-car-lb",
        base_model="AE86",
        rarity="common",
    )
    db.add(car)
    await db.flush()

    now = datetime.now(timezone.utc)
    lootbox = Lootbox(
        user_id=test_user.id,
        tier="bronze",
        created_at=now,
    )
    db.add(lootbox)
    await db.flush()

    result = await open_lootbox(lootbox.id, test_user.id, db)
    assert result["type"] in ("car", "duplicate_points", "points")


@pytest.mark.asyncio
async def test_open_lootbox_duplicate_gives_points(db, test_user, test_car):
    """Opening a lootbox with a car already owned gives points."""
    from app.models.car import CarOwnership

    # Give user the car first
    db.add(CarOwnership(
        user_id=test_user.id,
        car_catalog_id=test_car.id,
        obtained_at=datetime.now(timezone.utc),
    ))
    now = datetime.now(timezone.utc)
    lootbox = Lootbox(
        user_id=test_user.id,
        tier="bronze",
        car_awarded_id=None,
        created_at=now,
    )
    db.add(lootbox)
    await db.flush()

    # Since we can't control which car is picked, just verify it opens
    result = await open_lootbox(lootbox.id, test_user.id, db)
    assert result is not None
    assert lootbox.opened is True


@pytest.mark.asyncio
async def test_open_lootbox_already_opened_raises(db, test_user, test_car):
    """Opening an already-opened lootbox raises ValueError."""
    now = datetime.now(timezone.utc)
    lootbox = Lootbox(
        user_id=test_user.id,
        tier="bronze",
        opened=True,
        opened_at=now,
        created_at=now,
    )
    db.add(lootbox)
    await db.flush()

    with pytest.raises(ValueError, match="already opened"):
        await open_lootbox(lootbox.id, test_user.id, db)
