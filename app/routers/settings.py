import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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


@router.get("/leetcode/debug")
async def leetcode_debug(
    username: str,
    current_user: User = Depends(get_current_user),
):
    """Return raw responses from the LeetCode API for a given username."""
    base = settings.lc_api_base_url.rstrip("/")
    results: dict = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Profile endpoint
        try:
            r = await client.get(f"{base}/{username}")
            results["profile"] = {
                "status_code": r.status_code,
                "body": r.json() if "application/json" in r.headers.get("content-type", "") else r.text[:500],
            }
        except Exception as e:
            results["profile"] = {"error": str(e)}

        # Submission endpoint
        try:
            r = await client.get(f"{base}/{username}/submission", params={"limit": 5})
            results["submission"] = {
                "status_code": r.status_code,
                "body": r.json() if "application/json" in r.headers.get("content-type", "") else r.text[:500],
            }
        except Exception as e:
            results["submission"] = {"error": str(e)}

        # Accepted submission endpoint
        try:
            r = await client.get(f"{base}/{username}/acSubmission", params={"limit": 5})
            results["ac_submission"] = {
                "status_code": r.status_code,
                "body": r.json() if "application/json" in r.headers.get("content-type", "") else r.text[:500],
            }
        except Exception as e:
            results["ac_submission"] = {"error": str(e)}

    return {"base_url": base, "username": username, "results": results}
