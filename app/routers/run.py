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
    TodayChallengeDetail,
    TodayStatusResponse,
    TrackInfo,
    UserSummary,
)
from app.services.processor import (
    CatchUpSummary,
    TodayStatus,
    get_or_create_run,
    process_today_phase1,
    process_today_phase2,
    process_user_days,
)

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


def _today_status_response(status: TodayStatus) -> TodayStatusResponse:
    return TodayStatusResponse(
        qualified=status.qualified,
        streak_applied=status.streak_applied,
        segment_advanced=status.segment_advanced,
        has_challenges=status.has_challenges,
        all_challenges_met=status.all_challenges_met,
        challenges=[
            TodayChallengeDetail(
                event_type=c.event_type,
                corner_type=c.corner_type,
                weather_type=c.weather_type,
                ghost_name=c.ghost_name,
                ghost_difficulty=c.ghost_difficulty,
                requirement=c.requirement,
                current_value=c.current_value,
                met=c.met,
                time_save_seconds=c.time_save_seconds,
                penalty_seconds=c.penalty_seconds,
            )
            for c in status.challenges
        ],
    )


@router.get("", response_model=RunResponse)
async def get_run(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current run state. Triggers catch-up processing for unprocessed past days,
    then runs Phase 1 for today (qualify streak, roll events)."""
    tz = ZoneInfo(current_user.timezone)
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)

    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )

    catchup_summary = None

    # Past-day catch-up (up to yesterday only)
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
            await db.refresh(current_user)

    # Phase 1: qualify today — increments streak, rolls events, may advance segment immediately
    today_status_data = await process_today_phase1(current_user, db)
    await db.refresh(current_user)

    # Re-fetch run after potential changes
    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )

    # Ensure there's always a run (brand-new user with no activity yet)
    if active_run is None:
        active_run, _ = await get_or_create_run(current_user, db)
        await db.commit()

    run_state = None
    if active_run:
        track = await db.get(Track, active_run.track_id)
        run_state = _run_state(active_run, track)

    return RunResponse(
        run=run_state,
        user=_user_summary(current_user),
        catchup_summary=catchup_summary,
        today_status=_today_status_response(today_status_data),
    )


@router.post("/process", response_model=RunResponse)
async def process_run(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-evaluate today's challenges with fresh activity.
    If all challenges are met, advances the segment.
    Also catches up any unprocessed past days first.
    """
    tz = ZoneInfo(current_user.timezone)
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)

    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )

    catchup_summary = None

    # Past-day catch-up
    if active_run and active_run.last_processed_date and active_run.last_processed_date < yesterday:
        from_date = active_run.last_processed_date + timedelta(days=1)
        to_date = yesterday
        if from_date <= to_date:
            summary = await process_user_days(current_user.id, from_date, to_date, db)
            catchup_summary = _summary_response(summary)
            await db.refresh(current_user)

    # Phase 2: resolve today's challenges
    today_status_data = await process_today_phase2(current_user, db, force_finalize=False)
    await db.refresh(current_user)

    # Re-fetch run
    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )
    if active_run is None:
        active_run, _ = await get_or_create_run(current_user, db)
        await db.commit()

    run_state = None
    if active_run:
        track = await db.get(Track, active_run.track_id)
        run_state = _run_state(active_run, track)

    return RunResponse(
        run=run_state,
        user=_user_summary(current_user),
        catchup_summary=catchup_summary,
        today_status=_today_status_response(today_status_data),
    )
