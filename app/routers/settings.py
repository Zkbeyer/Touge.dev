from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.services.leetcode import LeetCodeClient

router = APIRouter(prefix="/settings", tags=["settings"])


class LeetCodeRequest(BaseModel):
    username: str


@router.put("/leetcode")
async def set_leetcode(
    body: LeetCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate and set LeetCode username."""
    username = body.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    client = LeetCodeClient()
    valid = await client.validate_username(username)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"LeetCode username '{username}' could not be validated",
        )

    current_user.leetcode_username = username
    current_user.leetcode_validated = True
    await db.commit()
    return {"detail": "LeetCode username validated and saved", "username": username}


@router.delete("/leetcode")
async def remove_leetcode(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove LeetCode username and disable LC events."""
    current_user.leetcode_username = None
    current_user.leetcode_validated = False
    await db.commit()
    return {"detail": "LeetCode integration removed"}
