from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.reward import PersonalBest
from app.models.stats import LifetimeStats
from app.models.track import Track
from app.models.user import User
from app.schemas.profile import LifetimeStatsResponse, PersonalBestResponse, ProfileResponse

router = APIRouter(prefix="/profile", tags=["profile"])


def _format_seconds(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user profile with lifetime stats and personal bests."""
    stats = await db.get(LifetimeStats, current_user.id)

    pbs_rows = (await db.scalars(
        select(PersonalBest)
        .where(PersonalBest.user_id == current_user.id)
        .order_by(PersonalBest.best_seconds)
    )).all()

    pbs = []
    for pb in pbs_rows:
        track = await db.get(Track, pb.track_id)
        pbs.append(PersonalBestResponse(
            track_id=str(pb.track_id),
            track_name=track.name,
            track_slug=track.slug,
            best_seconds=pb.best_seconds,
            best_formatted=_format_seconds(pb.best_seconds),
            set_at=pb.set_at,
        ))

    stats_response = LifetimeStatsResponse(
        total_runs_completed=stats.total_runs_completed if stats else 0,
        total_days_qualified=stats.total_days_qualified if stats else 0,
        total_gas_used=stats.total_gas_used if stats else 0,
        total_crashes=stats.total_crashes if stats else 0,
        total_corner_saves=stats.total_corner_saves if stats else 0,
        total_weather_survived=stats.total_weather_survived if stats else 0,
        total_ghost_wins=stats.total_ghost_wins if stats else 0,
        total_lootboxes_opened=stats.total_lootboxes_opened if stats else 0,
        total_cars_owned=stats.total_cars_owned if stats else 0,
    )

    return ProfileResponse(
        id=str(current_user.id),
        github_username=current_user.github_username,
        display_name=current_user.display_name,
        email=current_user.email,
        streak=current_user.streak,
        longest_streak=current_user.longest_streak,
        total_points=current_user.total_points,
        spendable_points=current_user.spendable_points,
        gas=current_user.gas,
        leetcode_username=current_user.leetcode_username,
        leetcode_validated=current_user.leetcode_validated,
        lifetime_stats=stats_response,
        personal_bests=pbs,
    )


@router.get("/pbs")
async def get_personal_bests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all personal best times."""
    pbs_rows = (await db.scalars(
        select(PersonalBest)
        .where(PersonalBest.user_id == current_user.id)
        .order_by(PersonalBest.best_seconds)
    )).all()

    result = []
    for pb in pbs_rows:
        track = await db.get(Track, pb.track_id)
        result.append(PersonalBestResponse(
            track_id=str(pb.track_id),
            track_name=track.name,
            track_slug=track.slug,
            best_seconds=pb.best_seconds,
            best_formatted=_format_seconds(pb.best_seconds),
            set_at=pb.set_at,
        ))
    return result
