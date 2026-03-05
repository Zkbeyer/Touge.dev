from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.run import Run
from app.models.track import Track
from app.models.user import User
from app.schemas.run import (
    CatchUpSummaryResponse,
    RunResponse,
    RunState,
    SummaryDayResponse,
    TrackInfo,
    UserSummary,
)
from app.services.processor import CatchUpSummary, process_user_days

router = APIRouter(prefix="/run", tags=["run"])


def _user_summary(user: User) -> UserSummary:
    return UserSummary(
        id=str(user.id),
        github_username=user.github_username,
        streak=user.streak,
        longest_streak=user.longest_streak,
        gas=user.gas,
        total_points=user.total_points,
        spendable_points=user.spendable_points,
    )


def _run_state(run: Run, track: Track) -> RunState:
    return RunState(
        id=str(run.id),
        track=TrackInfo(
            id=str(track.id),
            name=track.name,
            slug=track.slug,
            length_days=track.length_days,
            difficulty=track.difficulty,
        ),
        segment_index=run.segment_index,
        stopwatch_seconds=run.stopwatch_seconds,
        corner_saves=run.corner_saves,
        weather_penalties_taken=run.weather_penalties_taken,
        ghost_wins=run.ghost_wins,
        start_date=run.start_date,
        last_processed_date=run.last_processed_date,
    )


def _summary_response(summary: CatchUpSummary) -> CatchUpSummaryResponse:
    return CatchUpSummaryResponse(
        days_processed=summary.days_processed,
        net_streak_change=summary.net_streak_change,
        gas_used=summary.gas_used,
        crashed=summary.crashed,
        stopwatch_delta=summary.stopwatch_delta,
        ghost_wins=summary.ghost_wins,
        run_completed=summary.run_completed,
        lootboxes_awarded=summary.lootboxes_awarded,
        days=[
            SummaryDayResponse(
                date=d.date,
                qualified=d.qualified,
                gas_used=d.gas_used,
                crashed=d.crashed,
                corner_completed=d.corner_completed,
                weather_survived=d.weather_survived,
                ghost_won=d.ghost_won,
                stopwatch_delta=d.stopwatch_delta,
                ghost_points=d.ghost_points,
            )
            for d in summary.days
        ],
    )


@router.get("", response_model=RunResponse)
async def get_run(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current run state. Triggers catch-up processing for unprocessed days."""
    tz = ZoneInfo(current_user.timezone)
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)

    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )

    catchup_summary = None

    # Determine if catch-up is needed
    needs_catchup = False
    if active_run is None:
        needs_catchup = True
    elif active_run.last_processed_date is None or active_run.last_processed_date < yesterday:
        needs_catchup = True

    if needs_catchup:
        from_date = active_run.last_processed_date + timedelta(days=1) if (active_run and active_run.last_processed_date) else (active_run.start_date if active_run else today)
        to_date = yesterday

        if from_date <= to_date:
            summary = await process_user_days(current_user.id, from_date, to_date, db)
            catchup_summary = _summary_response(summary)
            # Refresh user state
            await db.refresh(current_user)

    # Re-fetch run after potential changes
    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )

    run_state = None
    if active_run:
        track = await db.get(Track, active_run.track_id)
        run_state = _run_state(active_run, track)

    return RunResponse(
        run=run_state,
        user=_user_summary(current_user),
        catchup_summary=catchup_summary,
    )


@router.post("/process", response_model=CatchUpSummaryResponse)
async def process_run(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger catch-up processing, including today.
    Useful when user wants to process the current day immediately.
    """
    tz = ZoneInfo(current_user.timezone)
    today = datetime.now(tz).date()

    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )

    if active_run and active_run.last_processed_date:
        from_date = active_run.last_processed_date + timedelta(days=1)
    elif active_run:
        from_date = active_run.start_date
    else:
        from_date = today

    to_date = today

    if from_date > to_date:
        return CatchUpSummaryResponse(
            days_processed=0,
            net_streak_change=0,
            gas_used=0,
            crashed=False,
            stopwatch_delta=0,
            ghost_wins=0,
            run_completed=False,
            lootboxes_awarded=0,
            days=[],
        )

    summary = await process_user_days(current_user.id, from_date, to_date, db)
    return _summary_response(summary)
