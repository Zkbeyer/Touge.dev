"""
########################################################################
# !! TEST HELPERS — DELETE BEFORE PRODUCTION !!
# All routes are prefixed /test and require auth.
# These endpoints bypass normal game flow for local testing only.
########################################################################
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.activity import DailyActivity
from app.services.activity import _decrypt_token
from app.services.github import GitHubClient
from app.services.leetcode import LeetCodeClient
from app.models.car import CarCatalog, CarOwnership
from app.models.cosmetic import CosmeticInventory
from app.models.event import DailyProcessedDay, DailyRunEvents
from app.models.reward import Lootbox, PersonalBest
from app.models.run import CompletedRun, Run
from app.models.stats import LifetimeStats
from app.models.track import Track
from app.models.user import User
from app.services.events import (
    CORNER_CHALLENGES,
    CORNER_SAVES,
    WEATHER_CHALLENGES,
    WEATHER_PENALTIES,
    _generate_weather_requirement,
    _pick_corner_challenge,
    _pick_weather_challenge,
    _roll,
)
from app.services.processor import (
    CatchUpSummary,
    TodayStatus,
    _today_for_user,
    get_or_create_run,
    process_today_phase1,
    process_today_phase2,
    process_user_days,
)

router = APIRouter(prefix="/test", tags=["!! TEST HELPERS — DELETE BEFORE PROD !!"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_test_date(run: Run) -> date:
    """Return the next unprocessed date for this run."""
    if run.last_processed_date:
        return run.last_processed_date + timedelta(days=1)
    return run.start_date


async def _inject_activity(
    user_id,
    target_date: date,
    commits: int,
    lc_easy: int,
    lc_medium: int,
    lc_hard: int,
    db: AsyncSession,
    repos: int = 1,
) -> None:
    """Upsert daily_activity and clear any existing processed-day record so
    the processor treats this date as fresh."""
    lc_total = lc_easy + lc_medium + lc_hard
    stmt = pg_insert(DailyActivity).values(
        user_id=user_id,
        date=target_date,
        github_commit_count=commits,
        github_repo_count=repos,
        lc_easy_accepted=lc_easy,
        lc_medium_accepted=lc_medium,
        lc_hard_accepted=lc_hard,
        lc_total_accepted=lc_total,
        fetched_at=datetime.now(timezone.utc),
        is_finalized=True,
    ).on_conflict_do_update(
        constraint="uq_daily_activity_user_date",
        set_={
            "github_commit_count": commits,
            "github_repo_count": repos,
            "lc_easy_accepted": lc_easy,
            "lc_medium_accepted": lc_medium,
            "lc_hard_accepted": lc_hard,
            "lc_total_accepted": lc_total,
            "fetched_at": datetime.now(timezone.utc),
            "is_finalized": True,
        },
    )
    await db.execute(stmt)

    # Remove any existing processed-day record so the processor runs fresh
    await db.execute(
        delete(DailyProcessedDay).where(
            DailyProcessedDay.user_id == user_id,
            DailyProcessedDay.date == target_date,
        )
    )
    # Also clear stale event rolls for this date so they re-roll if needed
    await db.execute(
        delete(DailyRunEvents).where(
            DailyRunEvents.user_id == user_id,
            DailyRunEvents.date == target_date,
        )
    )
    await db.flush()


def _serialize_summary(s: CatchUpSummary) -> dict:
    return {
        "days_processed": s.days_processed,
        "net_streak_change": s.net_streak_change,
        "gas_used": s.gas_used,
        "crashed": s.crashed,
        "stopwatch_delta": s.stopwatch_delta,
        # "ghost_wins": s.ghost_wins,        # ghost removed
        "run_completed": s.run_completed,
        # "lootboxes_awarded": s.lootboxes_awarded,  # lootbox removed
        "days": [
            {
                "date": str(d.date),
                "qualified": d.qualified,
                "gas_used": d.gas_used,
                "crashed": d.crashed,
                "segment_advanced": d.segment_advanced,
                "run_completed": d.run_completed,
                "stopwatch_delta": d.stopwatch_delta,
                "corner_completed": d.corner_completed,
                "weather_survived": d.weather_survived,
                # "ghost_won": d.ghost_won,      # ghost removed
                # "ghost_points": d.ghost_points,  # ghost removed
            }
            for d in s.days
        ],
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InjectActivityBody(BaseModel):
    target_date: date | None = None   # defaults to next unprocessed date
    commits: int = 1
    repos: int = 1
    lc_easy: int = 0
    lc_medium: int = 0
    lc_hard: int = 0


class ProcessDayBody(BaseModel):
    """Inject activity for a date and immediately process it through the full pipeline."""
    target_date: date | None = None   # defaults to next unprocessed date
    commits: int = 1
    repos: int = 1
    lc_easy: int = 0
    lc_medium: int = 0
    lc_hard: int = 0


class FastForwardBody(BaseModel):
    days: int = 1                     # number of qualified days to advance
    commits_per_day: int = 1


class GivePointsBody(BaseModel):
    amount: int = 500


class GiveGasBody(BaseModel):
    amount: int = 1


class GiveLootboxBody(BaseModel):
    tier: str = "gold"                # bronze | silver | gold | platinum
    count: int = 1


class SetSegmentBody(BaseModel):
    segment_index: int


class ForceWeatherBody(BaseModel):
    weather_type: str  # fog | rain | night_run


# ---------------------------------------------------------------------------
# 1. Inject activity for a date (no processing — just seeds the activity row)
# ---------------------------------------------------------------------------

@router.post("/activity/inject")
async def test_inject_activity(
    body: InjectActivityBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seed a daily_activity row for a date. Does NOT process it through the game loop."""
    run, _ = await get_or_create_run(current_user, db)

    target_date = body.target_date or _next_test_date(run)
    await _inject_activity(
        current_user.id, target_date,
        body.commits, body.lc_easy, body.lc_medium, body.lc_hard, db,
        repos=body.repos,
    )
    await db.commit()
    return {
        "injected_date": str(target_date),
        "commits": body.commits,
        "repos": body.repos,
        "lc_easy": body.lc_easy,
        "lc_medium": body.lc_medium,
        "lc_hard": body.lc_hard,
        "note": "Call POST /test/run/process-day with this date to push it through the game loop.",
    }


# ---------------------------------------------------------------------------
# 2. Inject + process a single day (main "advance one day" test endpoint)
# ---------------------------------------------------------------------------

def _serialize_today_status(status: TodayStatus) -> dict:
    return {
        "qualified": status.qualified,
        "streak_applied": status.streak_applied,
        "segment_advanced": status.segment_advanced,
        "has_challenges": status.has_challenges,
        "all_challenges_met": status.all_challenges_met,
        "challenges": [
            {
                "event_type": c.event_type,
                "corner_type": c.corner_type,
                "weather_type": c.weather_type,
                # "ghost_name": c.ghost_name,          # ghost removed
                # "ghost_difficulty": c.ghost_difficulty, # ghost removed
                "requirement": c.requirement,
                "current_value": c.current_value,
                "required_value": c.required_value,
                "met": c.met,
                "time_save_seconds": c.time_save_seconds,
                "penalty_seconds": c.penalty_seconds,
            }
            for c in status.challenges
        ],
    }


@router.post("/run/process-day")
async def test_process_day(
    body: ProcessDayBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inject activity and run it through the full processor pipeline for one day.
    If target_date is today (real calendar today), uses Phase 1 + Phase 2 with force_finalize=True
    so segment always advances regardless of pending challenges.
    If target_date is in the past, uses process_user_days directly."""
    run, track = await get_or_create_run(current_user, db)

    target_date = body.target_date or _next_test_date(run)
    await _inject_activity(
        current_user.id, target_date,
        body.commits, body.lc_easy, body.lc_medium, body.lc_hard, db,
        repos=body.repos,
    )
    await db.commit()

    today = _today_for_user(current_user)
    summary_data = None
    today_status_data = None

    if target_date == today:
        # Phase 1: qualify + roll events
        phase1_status = await process_today_phase1(current_user, db)
        await db.refresh(current_user)
        # Phase 2 with force_finalize so segment always advances
        today_status_data = await process_today_phase2(current_user, db, force_finalize=True)
        await db.refresh(current_user)
    else:
        summary = await process_user_days(current_user.id, target_date, target_date, db)
        summary_data = _serialize_summary(summary)
        await db.refresh(current_user)

    # Re-fetch run state after processing
    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )
    run_info = None
    if active_run:
        t = await db.get(Track, active_run.track_id)
        run_info = {
            "segment_index": active_run.segment_index,
            "track_name": t.name if t else None,
            "track_length_days": t.length_days if t else None,
            "stopwatch_seconds": active_run.stopwatch_seconds,
        }

    result = {
        "processed_date": str(target_date),
        "user": {
            "streak": current_user.streak,
            "gas": current_user.gas,
            "total_points": current_user.total_points,
            "spendable_points": current_user.spendable_points,
        },
        "active_run": run_info,
    }
    if summary_data is not None:
        result["summary"] = summary_data
    if today_status_data is not None:
        result["today_status"] = _serialize_today_status(today_status_data)
    return result


# ---------------------------------------------------------------------------
# 3. Fast-forward N days (auto-inject + process N qualified days in sequence)
# ---------------------------------------------------------------------------

@router.post("/run/fast-forward")
async def test_fast_forward(
    body: FastForwardBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process N qualified days in sequence. Each day gets commits_per_day commits."""
    if body.days < 1 or body.days > 60:
        raise HTTPException(status_code=400, detail="days must be between 1 and 60")

    run, _ = await get_or_create_run(current_user, db)
    next_date = _next_test_date(run)

    all_summaries = []
    for i in range(body.days):
        target_date = next_date + timedelta(days=i)
        await _inject_activity(
            current_user.id, target_date,
            body.commits_per_day, 0, 0, 0, db,
        )
        summary = await process_user_days(current_user.id, target_date, target_date, db)
        all_summaries.append(_serialize_summary(summary))
        # Re-fetch run for the next iteration's _next_test_date
        run = await db.scalar(
            select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
        )
        if run is None:
            break  # run completed and a new one started — stop here

    await db.refresh(current_user)
    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )
    run_info = None
    if active_run:
        t = await db.get(Track, active_run.track_id)
        run_info = {
            "segment_index": active_run.segment_index,
            "track_name": t.name if t else None,
            "track_length_days": t.length_days if t else None,
            "stopwatch_seconds": active_run.stopwatch_seconds,
        }

    return {
        "days_requested": body.days,
        "days_run": len(all_summaries),
        "summaries": all_summaries,
        "user": {
            "streak": current_user.streak,
            "gas": current_user.gas,
            "total_points": current_user.total_points,
            "spendable_points": current_user.spendable_points,
        },
        "active_run": run_info,
    }


# ---------------------------------------------------------------------------
# 4. Skip to run completion (process enough days to finish the current track)
# ---------------------------------------------------------------------------

@router.post("/run/skip-to-completion")
async def test_skip_to_completion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fast-forward exactly enough days to complete the current run track."""
    run, track = await get_or_create_run(current_user, db)

    remaining = track.length_days - run.segment_index
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Run already complete or at final segment.")

    next_date = _next_test_date(run)
    all_summaries = []
    for i in range(remaining):
        target_date = next_date + timedelta(days=i)
        await _inject_activity(current_user.id, target_date, 1, 0, 0, 0, db)
        summary = await process_user_days(current_user.id, target_date, target_date, db)
        all_summaries.append(_serialize_summary(summary))
        run = await db.scalar(
            select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
        )
        if run is None:
            run, track = await get_or_create_run(current_user, db)
            break

    await db.refresh(current_user)
    active_run = await db.scalar(
        select(Run).where(Run.user_id == current_user.id, Run.is_complete == False)
    )
    run_info = None
    if active_run:
        t = await db.get(Track, active_run.track_id)
        run_info = {
            "segment_index": active_run.segment_index,
            "track_name": t.name if t else None,
            "track_length_days": t.length_days if t else None,
            "stopwatch_seconds": active_run.stopwatch_seconds,
        }

    return {
        "days_processed": len(all_summaries),
        "summaries": all_summaries,
        "user": {
            "streak": current_user.streak,
            "gas": current_user.gas,
            "total_points": current_user.total_points,
            "spendable_points": current_user.spendable_points,
        },
        "new_run": run_info,
    }


# ---------------------------------------------------------------------------
# 5. Force a crash (simulate a missed day with no gas)
# ---------------------------------------------------------------------------

@router.post("/run/force-crash")
async def test_force_crash(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inject a missed day (0 commits) and set gas=0 so the processor crashes the run."""
    run, _ = await get_or_create_run(current_user, db)
    target_date = _next_test_date(run)

    # Drain gas
    current_user.gas = 0
    await _inject_activity(current_user.id, target_date, 0, 0, 0, 0, db)
    summary = await process_user_days(current_user.id, target_date, target_date, db)
    await db.refresh(current_user)

    return {
        "crash_date": str(target_date),
        "summary": _serialize_summary(summary),
        "user": {
            "streak": current_user.streak,
            "gas": current_user.gas,
        },
    }


# ---------------------------------------------------------------------------
# 6. Directly set run segment_index (raw DB write — bypasses all game logic)
# ---------------------------------------------------------------------------

@router.post("/run/set-segment")
async def test_set_segment(
    body: SetSegmentBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Directly set segment_index on the active run. No events, no stopwatch changes."""
    run, track = await get_or_create_run(current_user, db)

    if body.segment_index < 0 or body.segment_index > track.length_days:
        raise HTTPException(
            status_code=400,
            detail=f"segment_index must be 0–{track.length_days}",
        )

    run.segment_index = body.segment_index
    await db.commit()
    return {
        "segment_index": run.segment_index,
        "track_length_days": track.length_days,
        "remaining_segments": track.length_days - run.segment_index,
    }


# ---------------------------------------------------------------------------
# 7. Give points
# ---------------------------------------------------------------------------

@router.post("/user/give-points")
async def test_give_points(
    body: GivePointsBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add points directly to the user (both total and spendable)."""
    current_user.total_points += body.amount
    current_user.spendable_points += body.amount
    await db.commit()
    return {
        "added": body.amount,
        "total_points": current_user.total_points,
        "spendable_points": current_user.spendable_points,
    }


# ---------------------------------------------------------------------------
# 8. Give gas
# ---------------------------------------------------------------------------

@router.post("/user/give-gas")
async def test_give_gas(
    body: GiveGasBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add gas canisters directly to the user."""
    current_user.gas += body.amount
    await db.commit()
    return {"added": body.amount, "gas": current_user.gas}


# ---------------------------------------------------------------------------
# 9. Give lootbox(es)
# ---------------------------------------------------------------------------

VALID_TIERS = {"bronze", "silver", "gold", "platinum"}

@router.post("/inventory/give-lootbox")
async def test_give_lootbox(
    body: GiveLootboxBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Directly award lootbox(es) to the user's inventory."""
    if body.tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"tier must be one of: {VALID_TIERS}")
    if body.count < 1 or body.count > 10:
        raise HTTPException(status_code=400, detail="count must be 1–10")

    now = datetime.now(timezone.utc)
    ids = []
    for _ in range(body.count):
        lb = Lootbox(
            user_id=current_user.id,
            tier=body.tier,
            source_run_id=None,
            created_at=now,
        )
        db.add(lb)
        await db.flush()
        ids.append(str(lb.id))

    await db.commit()
    return {"awarded": body.count, "tier": body.tier, "lootbox_ids": ids}


# ---------------------------------------------------------------------------
# 10. Set streak directly
# ---------------------------------------------------------------------------

class SetStreakBody(BaseModel):
    streak: int = 0


@router.post("/user/set-streak")
async def test_set_streak(
    body: SetStreakBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set user streak to any value for testing perk thresholds etc."""
    current_user.streak = max(0, body.streak)
    await db.commit()
    return {"streak": current_user.streak}


# ---------------------------------------------------------------------------
# 11. Full debug state dump
# ---------------------------------------------------------------------------

@router.get("/state")
async def test_get_state(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dump complete debug state: user, active run, recent activity, recent events."""
    run, track = await get_or_create_run(current_user, db)

    # Recent activity (last 7 days)
    recent_activity = (await db.scalars(
        select(DailyActivity)
        .where(DailyActivity.user_id == current_user.id)
        .order_by(DailyActivity.date.desc())
        .limit(7)
    )).all()

    # Recent processed days (last 7)
    recent_processed = (await db.scalars(
        select(DailyProcessedDay)
        .where(DailyProcessedDay.user_id == current_user.id)
        .order_by(DailyProcessedDay.date.desc())
        .limit(7)
    )).all()

    # Recent events (last 7)
    recent_events = (await db.scalars(
        select(DailyRunEvents)
        .where(DailyRunEvents.user_id == current_user.id)
        .order_by(DailyRunEvents.date.desc())
        .limit(7)
    )).all()

    # Unopened lootboxes
    lootboxes = (await db.scalars(
        select(Lootbox)
        .where(Lootbox.user_id == current_user.id, Lootbox.opened == False)
    )).all()

    stats = await db.get(LifetimeStats, current_user.id)

    return {
        "user": {
            "id": str(current_user.id),
            "github_username": current_user.github_username,
            "streak": current_user.streak,
            "longest_streak": current_user.longest_streak,
            "gas": current_user.gas,
            "total_points": current_user.total_points,
            "spendable_points": current_user.spendable_points,
            "active_car_id": str(current_user.active_car_id) if current_user.active_car_id else None,
            "leetcode_validated": current_user.leetcode_validated,
        },
        "active_run": {
            "id": str(run.id),
            "track_name": track.name,
            "track_slug": track.slug,
            "track_difficulty": track.difficulty,
            "track_length_days": track.length_days,
            "segment_index": run.segment_index,
            "segments_remaining": track.length_days - run.segment_index,
            "stopwatch_seconds": run.stopwatch_seconds,
            "corner_saves": run.corner_saves,
            "weather_penalties_taken": run.weather_penalties_taken,
            "ghost_wins": run.ghost_wins,
            "start_date": str(run.start_date),
            "last_processed_date": str(run.last_processed_date) if run.last_processed_date else None,
            "next_test_date": str(_next_test_date(run)),
            "momentum_used": run.momentum_used,
        },
        "recent_activity": [
            {
                "date": str(a.date),
                "commits": a.github_commit_count,
                "repos": a.github_repo_count,
                "lc_total": a.lc_total_accepted,
                "is_finalized": a.is_finalized,
            }
            for a in recent_activity
        ],
        "recent_processed_days": [
            {
                "date": str(p.date),
                "qualified": p.qualified,
                "gas_used": p.gas_used,
                "crashed": p.crashed,
                "segment_advanced": p.segment_advanced,
                "run_completed": p.run_completed,
                "stopwatch_delta": p.stopwatch_delta,
            }
            for p in recent_processed
        ],
        "recent_events": [
            {
                "date": str(e.date),
                "corner_type": e.corner_type,
                "corner_completed": e.corner_completed,
                "weather_type": e.weather_type,
                "weather_survived": e.weather_survived,
                "ghost_name": e.ghost_name,
                "ghost_difficulty": e.ghost_difficulty,
                "ghost_won": e.ghost_won,
                "processed": e.processed,
            }
            for e in recent_events
        ],
        "unopened_lootboxes": [
            {"id": str(lb.id), "tier": lb.tier, "created_at": str(lb.created_at)}
            for lb in lootboxes
        ],
        "lifetime_stats": {
            "total_runs_completed": stats.total_runs_completed if stats else 0,
            "total_days_qualified": stats.total_days_qualified if stats else 0,
            "total_crashes": stats.total_crashes if stats else 0,
            "total_corner_saves": stats.total_corner_saves if stats else 0,
            "total_ghost_wins": stats.total_ghost_wins if stats else 0,
            "total_cars_owned": stats.total_cars_owned if stats else 0,
            "total_lootboxes_opened": stats.total_lootboxes_opened if stats else 0,
        },
    }


# ---------------------------------------------------------------------------
# 12. Full account reset (wipe all game data, keep auth)
# ---------------------------------------------------------------------------

@router.post("/user/reset")
async def test_reset_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Wipe all game data for the current user and return them to a fresh state.
    OAuth tokens and profile info (username, timezone, LeetCode settings) are preserved."""
    uid = current_user.id

    # Delete all user-owned game rows (CASCADE handles children where set,
    # but explicit deletes are clearer and avoid ordering issues)
    await db.execute(delete(DailyRunEvents).where(DailyRunEvents.user_id == uid))
    await db.execute(delete(DailyProcessedDay).where(DailyProcessedDay.user_id == uid))
    await db.execute(delete(DailyActivity).where(DailyActivity.user_id == uid))
    await db.execute(delete(Lootbox).where(Lootbox.user_id == uid))
    await db.execute(delete(PersonalBest).where(PersonalBest.user_id == uid))
    await db.execute(delete(CosmeticInventory).where(CosmeticInventory.user_id == uid))
    await db.execute(delete(CarOwnership).where(CarOwnership.user_id == uid))
    await db.execute(delete(CompletedRun).where(CompletedRun.user_id == uid))
    await db.execute(delete(Run).where(Run.user_id == uid))

    # Reset user stats fields
    current_user.streak = 0
    current_user.longest_streak = 0
    current_user.gas = 0
    current_user.total_points = 0
    current_user.spendable_points = 0
    current_user.active_car_id = None

    # Reset lifetime stats
    stats = await db.get(LifetimeStats, uid)
    if stats:
        stats.total_runs_completed = 0
        stats.total_days_qualified = 0
        stats.total_gas_used = 0
        stats.total_crashes = 0
        stats.total_corner_saves = 0
        stats.total_weather_survived = 0
        stats.total_ghost_wins = 0
        stats.total_lootboxes_opened = 0
        stats.total_cars_owned = 0

    # Re-award starter car
    ae86 = await db.scalar(select(CarCatalog).where(CarCatalog.slug == "ae86-trueno"))
    if ae86:
        db.add(CarOwnership(
            user_id=uid,
            car_catalog_id=ae86.id,
            obtained_at=datetime.now(timezone.utc),
        ))
        current_user.active_car_id = ae86.id
        if stats:
            stats.total_cars_owned = 1

    await db.commit()
    return {
        "reset": True,
        "user": {
            "id": str(current_user.id),
            "github_username": current_user.github_username,
            "streak": 0,
            "gas": 0,
            "total_points": 0,
            "spendable_points": 0,
            "active_car_id": str(current_user.active_car_id) if current_user.active_car_id else None,
        },
        "note": "All game data wiped. Starter car re-awarded. Call GET /run to start fresh.",
    }


# ---------------------------------------------------------------------------
# 13. Advance date by 1 day (no game logic — pure date skip)
# ---------------------------------------------------------------------------

@router.post("/run/advance-date")
async def test_advance_date(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bump last_processed_date by 1 day and clear today's processed state so GET /run starts fresh."""
    run, _ = await get_or_create_run(current_user, db)

    if run.last_processed_date is None:
        run.last_processed_date = run.start_date
    else:
        run.last_processed_date = run.last_processed_date + timedelta(days=1)

    # Clear the real calendar today's records so the processor treats it as a new day
    today = _today_for_user(current_user)
    await db.execute(
        delete(DailyProcessedDay).where(
            DailyProcessedDay.user_id == current_user.id,
            DailyProcessedDay.date == today,
        )
    )
    await db.execute(
        delete(DailyRunEvents).where(
            DailyRunEvents.user_id == current_user.id,
            DailyRunEvents.date == today,
        )
    )

    await db.commit()
    next_test = run.last_processed_date + timedelta(days=1)
    return {
        "advanced_to": str(run.last_processed_date),
        "next_test_date": str(next_test),
    }


# ---------------------------------------------------------------------------
# 14. Event pool inspector
# ---------------------------------------------------------------------------

@router.get("/events/pool")
async def test_events_pool(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the full eligible challenge pool (corner + weather) at current run state,
    plus the deterministically picked challenge for today's date."""
    run, track = await get_or_create_run(current_user, db)
    has_lc = current_user.leetcode_validated
    tier = min(run.segment_index // 5, 3)

    layout = track.segment_layout or []
    current_segment = None
    if layout and run.segment_index < len(layout):
        seg = layout[run.segment_index]
        current_segment = {
            "index": run.segment_index,
            "type": seg.get("type"),
            "name": seg.get("name"),
        }

    today = _today_for_user(current_user)
    corner_pick_roll = _roll(current_user.id, today, "corner_challenge_pick")
    weather_pick_roll = _roll(current_user.id, today, "weather_challenge_pick")

    corners = [
        {
            "corner_type": ct,
            "time_save_seconds": CORNER_SAVES[ct],
            "pool": [
                c for c in CORNER_CHALLENGES[ct]
                if c["min_tier"] <= tier and (not c["requires_lc"] or has_lc)
            ],
            "picked": _pick_corner_challenge(ct, run.segment_index, has_lc, corner_pick_roll),
        }
        for ct in ["sweeper", "chicane", "hairpin"]
    ]

    weather = [
        {
            "weather_type": wt,
            "penalty_seconds": WEATHER_PENALTIES[wt],
            "pool": [c for c in WEATHER_CHALLENGES[wt] if not c["requires_lc"] or has_lc],
            "picked": _pick_weather_challenge(wt, has_lc, weather_pick_roll),
        }
        for wt in ["fog", "rain", "night_run"]
    ]

    return {
        "segment_index": run.segment_index,
        "tier": tier,
        "has_leetcode": has_lc,
        "current_segment": current_segment,
        "corners": corners,
        "weather": weather,
    }


# ---------------------------------------------------------------------------
# 15. Force weather on the next test date
# ---------------------------------------------------------------------------

VALID_WEATHER_TYPES = {"fog", "rain", "night_run"}


@router.post("/events/force-weather")
async def test_force_weather(
    body: ForceWeatherBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pre-seed a weather event for the next unprocessed date. Processor will use it instead of rolling."""
    if body.weather_type not in VALID_WEATHER_TYPES:
        raise HTTPException(status_code=400, detail=f"weather_type must be one of: {VALID_WEATHER_TYPES}")

    run, _ = await get_or_create_run(current_user, db)
    target_date = _next_test_date(run)
    has_lc = current_user.leetcode_validated

    weather_req = _generate_weather_requirement(body.weather_type, has_lc)
    weather_penalty = WEATHER_PENALTIES[body.weather_type]

    stmt = pg_insert(DailyRunEvents).values(
        user_id=current_user.id,
        run_id=run.id,
        date=target_date,
        segment_index=run.segment_index,
        weather_roll=0.01,       # below 0.25 threshold — weather always fires
        weather_type=body.weather_type,
        weather_requirement=weather_req,
        weather_penalty_seconds=weather_penalty,
        corner_roll=0.9,         # above 0.60 — no corner from roll
        corner_type=None,
        corner_requirement=None,
        corner_time_save_seconds=None,
        ghost_roll=0.9,          # above 0.30 — no ghost
        processed=False,
    ).on_conflict_do_update(
        constraint="uq_daily_run_events_user_date",
        set_={
            "weather_roll": 0.01,
            "weather_type": body.weather_type,
            "weather_requirement": weather_req,
            "weather_penalty_seconds": weather_penalty,
            "corner_type": None,
            "corner_requirement": None,
            "corner_time_save_seconds": None,
            "ghost_roll": 0.9,
            "processed": False,
        },
    )
    await db.execute(stmt)
    await db.commit()
    return {
        "forced_weather": body.weather_type,
        "for_date": str(target_date),
    }


# ---------------------------------------------------------------------------
# 16. Debug: fetch raw LeetCode accepted submissions for today
# ---------------------------------------------------------------------------

@router.get("/activity/leetcode-debug")
async def test_leetcode_activity_debug(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch raw LeetCode accepted submissions for today and the cached activity record.
    Requires leetcode_username to be set and validated.
    """
    today = _today_for_user(current_user)

    cached = await db.scalar(
        select(DailyActivity).where(
            DailyActivity.user_id == current_user.id,
            DailyActivity.date == today,
        )
    )

    submissions = []
    lc_error = None

    if not current_user.leetcode_username:
        lc_error = "No LeetCode username configured"
    else:
        try:
            lc = LeetCodeClient()
            submissions = await lc.fetch_submissions_debug(
                current_user.leetcode_username, today, current_user.timezone
            )
        except Exception as e:
            lc_error = str(e)

    return {
        "date": str(today),
        "user_timezone": current_user.timezone,
        "leetcode_username": current_user.leetcode_username,
        "leetcode_validated": current_user.leetcode_validated,
        "cached_activity": {
            "lc_easy": cached.lc_easy_accepted if cached else None,
            "lc_medium": cached.lc_medium_accepted if cached else None,
            "lc_hard": cached.lc_hard_accepted if cached else None,
            "lc_total": cached.lc_total_accepted if cached else None,
            "fetched_at": str(cached.fetched_at) if cached else None,
            "is_finalized": cached.is_finalized if cached else None,
        },
        "live_leetcode": {
            "submission_count": len(submissions),
            "error": lc_error,
            "submissions": submissions,
        },
    }


# ---------------------------------------------------------------------------
# 18. Debug: fetch raw GitHub push events for today
# ---------------------------------------------------------------------------

@router.get("/activity/github-debug")
async def test_github_activity_debug(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch raw GitHub push events for today and the cached activity record.
    Shows exactly what the API returns so you can diagnose missing commits.
    """
    today = _today_for_user(current_user)

    # Current cached activity in DB
    cached = await db.scalar(
        select(DailyActivity).where(
            DailyActivity.user_id == current_user.id,
            DailyActivity.date == today,
        )
    )

    # Force fresh fetch from GitHub
    access_token = await _decrypt_token(current_user.id, db)
    push_events = []
    github_error = None
    live_commit_count = None

    if access_token:
        try:
            gh = GitHubClient(access_token)
            push_events = await gh.fetch_push_events_debug(
                current_user.github_username, today, current_user.timezone
            )
            live_commit_count = len([e for e in push_events if "error" not in e])
        except Exception as e:
            github_error = str(e)
    else:
        github_error = "No OAuth token found for user"

    return {
        "date": str(today),
        "user_timezone": current_user.timezone,
        "github_username": current_user.github_username,
        "cached_activity": {
            "commit_count": cached.github_commit_count if cached else None,
            "fetched_at": str(cached.fetched_at) if cached else None,
            "is_finalized": cached.is_finalized if cached else None,
        },
        "live_github": {
            "commit_count": live_commit_count,
            "error": github_error,
            "push_events": push_events,
        },
    }
