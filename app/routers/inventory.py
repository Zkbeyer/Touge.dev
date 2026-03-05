import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.reward import Lootbox
from app.models.user import User
from app.services.lootbox import open_lootbox

router = APIRouter(prefix="/inventory", tags=["inventory"])


class LootboxListItem(BaseModel):
    id: str
    tier: str
    created_at: str


class OpenLootboxResponse(BaseModel):
    type: str  # "car" | "duplicate_points" | "points"
    rarity: str
    car_id: str | None = None
    car_name: str | None = None
    points: int | None = None


@router.get("/lootboxes")
async def list_lootboxes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all unopened lootboxes."""
    lootboxes = (await db.scalars(
        select(Lootbox)
        .where(Lootbox.user_id == current_user.id, Lootbox.opened == False)
        .order_by(Lootbox.created_at.desc())
    )).all()

    return [
        {"id": str(lb.id), "tier": lb.tier, "created_at": lb.created_at.isoformat()}
        for lb in lootboxes
    ]


@router.post("/lootboxes/{lootbox_id}/open", response_model=OpenLootboxResponse)
async def open_lootbox_endpoint(
    lootbox_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Open a lootbox. Returns the car awarded or points if duplicate."""
    try:
        result = await open_lootbox(lootbox_id, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return OpenLootboxResponse(**result)
