import secrets
import uuid
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.car import CarCatalog, CarOwnership
from app.models.oauth import OAuthToken
from app.models.stats import LifetimeStats
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from app.services.github import GitHubClient
from app.services.processor import get_or_create_run

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory CSRF state store (use Redis in production)
_oauth_states: dict[str, datetime] = {}


def _create_jwt(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


@router.get("/github")
async def github_oauth_redirect():
    """Redirect user to GitHub OAuth consent page."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = datetime.now(timezone.utc)
    # Clean expired states (> 10 minutes)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired = [k for k, v in _oauth_states.items() if v < cutoff]
    for k in expired:
        del _oauth_states[k]

    github_auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_redirect_uri}"
        f"&scope=read:user,user:email,repo"
        f"&state={state}"
    )
    return RedirectResponse(url=github_auth_url)


@router.get("/github/callback")
async def github_oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Handle GitHub OAuth callback. Upserts user and returns JWT."""
    # CSRF check
    if state not in _oauth_states:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    del _oauth_states[state]

    # Exchange code for token
    try:
        token_data = await GitHubClient.exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub token exchange failed: {e}")

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access token in GitHub response")

    # Fetch user info
    gh_client = GitHubClient(access_token)
    try:
        gh_user = await gh_client.get_user_info(access_token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub user fetch failed: {e}")

    github_id = gh_user["id"]
    github_username = gh_user["login"]
    email = gh_user.get("email")
    display_name = gh_user.get("name")

    # Upsert user
    stmt = insert(User).values(
        github_id=github_id,
        github_username=github_username,
        email=email,
        display_name=display_name,
    ).on_conflict_do_update(
        index_elements=["github_id"],
        set_={
            "github_username": github_username,
            "email": email,
            "display_name": display_name,
        },
    ).returning(User)
    result = await db.execute(stmt)
    user = result.scalar_one()

    # Ensure lifetime stats row exists; detect new user
    stats = await db.get(LifetimeStats, user.id)
    is_new_user = stats is None
    if is_new_user:
        stats = LifetimeStats(id=user.id, user_id=user.id)
        db.add(stats)
        await db.flush()  # so stats is tracked in session

        # Award starter car (ae86-trueno)
        ae86 = await db.scalar(select(CarCatalog).where(CarCatalog.slug == "ae86-trueno"))
        if ae86:
            db.add(CarOwnership(user_id=user.id, car_catalog_id=ae86.id, obtained_at=datetime.now(timezone.utc)))
            user.active_car_id = ae86.id
            stats.total_cars_owned += 1
            await db.flush()

        # Create initial run
        await get_or_create_run(user, db)

    # Encrypt and store token
    fernet = Fernet(settings.token_encryption_key.encode() if isinstance(settings.token_encryption_key, str) else settings.token_encryption_key)
    encrypted = fernet.encrypt(access_token.encode())

    token_stmt = insert(OAuthToken).values(
        user_id=user.id,
        provider="github",
        access_token_enc=encrypted,
        scope=token_data.get("scope"),
        token_type=token_data.get("token_type"),
    ).on_conflict_do_update(
        constraint="oauth_tokens_user_id_key",
        set_={
            "access_token_enc": encrypted,
            "scope": token_data.get("scope"),
            "token_type": token_data.get("token_type"),
        },
    )
    await db.execute(token_stmt)
    await db.commit()

    jwt_token = _create_jwt(user.id)
    new_flag = "1" if is_new_user else "0"
    return RedirectResponse(url=f"/?token={jwt_token}&new_user={new_flag}")


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout (JWT is stateless; client should discard the token)."""
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        github_username=current_user.github_username,
        display_name=current_user.display_name,
        email=current_user.email,
        timezone=current_user.timezone,
        streak=current_user.streak,
        longest_streak=current_user.longest_streak,
        total_points=current_user.total_points,
        spendable_points=current_user.spendable_points,
        gas=current_user.gas,
        leetcode_validated=current_user.leetcode_validated,
        leetcode_username=current_user.leetcode_username,
        active_car_id=str(current_user.active_car_id) if current_user.active_car_id else None,
    )
