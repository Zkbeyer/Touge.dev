import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.car import CarCatalog, CarOwnership, Perk
from app.models.cosmetic import Cosmetic, CosmeticInventory
from app.models.user import User
from app.schemas.garage import CosmeticResponse, OwnedCarResponse, CarCatalogInfo, PerkInfo, UpgradeResponse
from app.services.garage import select_car, toggle_perk, upgrade_car, UPGRADE_BASE_COSTS, RARITY_MULTIPLIERS

router = APIRouter(prefix="/garage", tags=["garage"])


async def _build_owned_car(ownership: CarOwnership, db: AsyncSession) -> OwnedCarResponse:
    car = await db.get(CarCatalog, ownership.car_catalog_id)
    perk = await db.get(Perk, car.perk_id) if car.perk_id else None
    perk_info = PerkInfo(
        id=str(perk.id),
        slug=perk.slug,
        name=perk.name,
        description=perk.description,
        effect_type=perk.effect_type,
        effect_value=perk.effect_value,
    ) if perk else None

    return OwnedCarResponse(
        id=str(ownership.id),
        car=CarCatalogInfo(
            id=str(car.id),
            name=car.name,
            slug=car.slug,
            rarity=car.rarity,
            description=car.description,
            base_model=car.base_model,
            max_upgrade_level=car.max_upgrade_level,
            perk=perk_info,
        ),
        upgrade_level=ownership.upgrade_level,
        iconic_unlocked=ownership.iconic_unlocked,
        perk_active=ownership.perk_active,
        obtained_at=ownership.obtained_at,
    )


@router.get("/cars")
async def get_garage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all owned cars."""
    ownerships = (await db.scalars(
        select(CarOwnership)
        .where(CarOwnership.user_id == current_user.id)
        .order_by(CarOwnership.obtained_at.desc())
    )).all()

    return [await _build_owned_car(o, db) for o in ownerships]


@router.post("/cars/{car_ownership_id}/select")
async def select_active_car(
    car_ownership_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set a car as the active car."""
    try:
        await select_car(current_user.id, car_ownership_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"detail": "Active car updated"}


@router.post("/cars/{car_ownership_id}/upgrade", response_model=UpgradeResponse)
async def upgrade_car_endpoint(
    car_ownership_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upgrade a car one level. Costs spendable_points."""
    try:
        result = await upgrade_car(current_user.id, car_ownership_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UpgradeResponse(**result)


class PerkToggleRequest(BaseModel):
    active: bool


@router.post("/cars/{car_ownership_id}/perk")
async def toggle_car_perk(
    car_ownership_id: uuid.UUID,
    body: PerkToggleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle perk active/inactive on a car (must be at max upgrade level)."""
    try:
        await toggle_perk(current_user.id, car_ownership_id, body.active, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"detail": f"Perk {'activated' if body.active else 'deactivated'}"}


@router.get("/cosmetics")
async def get_cosmetics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all owned cosmetics."""
    rows = (await db.scalars(
        select(CosmeticInventory)
        .where(CosmeticInventory.user_id == current_user.id)
        .order_by(CosmeticInventory.obtained_at.desc())
    )).all()

    result = []
    for inv in rows:
        cosmetic = await db.get(Cosmetic, inv.cosmetic_id)
        result.append(CosmeticResponse(
            id=str(cosmetic.id),
            slug=cosmetic.slug,
            name=cosmetic.name,
            type=cosmetic.type,
            rarity=cosmetic.rarity,
            source_description=cosmetic.source_description,
            obtained_at=inv.obtained_at,
        ))
    return result
