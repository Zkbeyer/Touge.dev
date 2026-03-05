import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import DailyActivity
from app.models.car import CarOwnership, Perk
from app.models.cosmetic import Cosmetic, CosmeticInventory
from app.models.event import DailyProcessedDay, DailyRunEvents
from app.models.reward import Lootbox, PersonalBest
from app.models.run import CompletedRun, Run
from app.models.stats import LifetimeStats
from app.models.track import Track
from app.models.user import User
from app.services.activity import get_or_fetch_activity
from app.services.events import GHOST_POINTS, evaluate_requirement, get_or_roll_events
from app.services.garage import user_has_active_perk
from app.services.lootbox import pick_lootbox_tier

BASE_GAS_CHANCE = 0.15


@dataclass
class SummaryDay:
    date: date
    qualified: bool
    gas_used: bool = False
    crashed: bool = False
    segment_advanced: bool = False
    run_completed: bool = False
    stopwatch_delta: int = 0
    corner_completed: bool | None = None
    weather_survived: bool | None = None
    ghost_won: bool | None = None
    ghost_points: int = 0


@dataclass
class CatchUpSummary:
    days: list[SummaryDay] = field(default_factory=list)
    days_processed: int = 0
    net_streak_change: int = 0
    gas_used: int = 0
    crashed: bool = False
    stopwatch_delta: int = 0
    ghost_wins: int = 0
    run_completed: bool = False
    lootboxes_awarded: int = 0


def _date_range(from_date: date, to_date: date):
    current = from_date
    while current <= to_date:
        yield current
        current += timedelta(days=1)


def _today_for_user(user: User) -> date:
    tz = ZoneInfo(user.timezone)
    return datetime.now(tz).date()


def _calculate_performance_score(run: Run, track: Track, user: User) -> int:
    score = track.length_days * 2
    score += run.corner_saves * 15
    score += (track.length_days - run.weather_penalties_taken) * 5
    score += run.ghost_wins * 10
    if user.streak >= 30:
        score += 20
    elif user.streak >= 14:
        score += 10
    elif user.streak >= 7:
        score += 5
    par_time = track.base_seconds_per_segment * track.length_days
    if run.stopwatch_seconds < par_time * 0.85:
        score += 20
    elif run.stopwatch_seconds < par_time:
        score += 10
    return score


async def _get_or_create_run(user: User, db: AsyncSession) -> tuple[Run, Track]:
    """Gets user's active run or creates a new one on a beginner track."""
    run = await db.scalar(
        select(Run).where(Run.user_id == user.id, Run.is_complete == False)
    )
    if run:
        track = await db.get(Track, run.track_id)
        return run, track

    # Pick a random beginner track (deterministic: first active beginner track by slug)
    track = await db.scalar(
        select(Track)
        .where(Track.is_active == True, Track.difficulty == "beginner")
        .order_by(Track.slug)
        .limit(1)
    )
    if not track:
        # Fallback to any active track
        track = await db.scalar(
            select(Track).where(Track.is_active == True).order_by(Track.slug).limit(1)
        )

    today = _today_for_user(user)
    run = Run(
        user_id=user.id,
        track_id=track.id,
        start_date=today,
    )
    db.add(run)
    await db.flush()
    return run, track


async def _start_new_run(user: User, exclude_track_id: uuid.UUID | None, db: AsyncSession) -> tuple[Run, Track]:
    """Starts a new run, preferring a different track than the last."""
    query = select(Track).where(Track.is_active == True)
    if exclude_track_id:
        query = query.where(Track.id != exclude_track_id)
    query = query.order_by(Track.difficulty, Track.slug).limit(1)

    track = await db.scalar(query)
    if not track:
        # Fallback: any track
        track = await db.scalar(
            select(Track).where(Track.is_active == True).order_by(Track.slug).limit(1)
        )

    today = _today_for_user(user)
    run = Run(
        user_id=user.id,
        track_id=track.id,
        start_date=today,
    )
    db.add(run)
    await db.flush()
    return run, track


async def _complete_run(
    user: User, run: Run, track: Track, db: AsyncSession
) -> Lootbox:
    from app.services.events import _roll

    now = datetime.now(timezone.utc)
    score = _calculate_performance_score(run, track, user)
    tier = pick_lootbox_tier(score)
    points = score * 3

    gas_roll = _roll(run.id, now.date(), "gas_drop")
    gas_chance = BASE_GAS_CHANCE
    if await user_has_active_perk(user.id, "lucky_find", db):
        gas_chance += 0.10
    gas_awarded = 1 if gas_roll < gas_chance else 0

    user.gas += gas_awarded
    user.total_points += points
    user.spendable_points += points

    # PB check
    pb = await db.scalar(
        select(PersonalBest).where(
            PersonalBest.user_id == user.id,
            PersonalBest.track_id == track.id,
        )
    )
    pb_set = False
    if not pb or run.stopwatch_seconds < pb.best_seconds:
        pb_set = True
        if pb:
            pb.best_seconds = run.stopwatch_seconds
            pb.set_at = now
            pb.run_id = run.id
        else:
            db.add(PersonalBest(
                user_id=user.id,
                track_id=track.id,
                best_seconds=run.stopwatch_seconds,
                set_at=now,
                run_id=run.id,
            ))

    lootbox = Lootbox(
        user_id=user.id,
        tier=tier,
        source_run_id=run.id,
        created_at=now,
    )
    db.add(lootbox)

    run.is_complete = True
    run.completed_at = now
    run.lootbox_tier = tier

    db.add(CompletedRun(
        user_id=user.id,
        track_id=track.id,
        run_id=run.id,
        completed_at=now,
        total_seconds=run.stopwatch_seconds,
        corner_saves=run.corner_saves,
        weather_penalties_taken=run.weather_penalties_taken,
        ghost_wins=run.ghost_wins,
        streak_at_completion=user.streak,
        lootbox_tier=tier,
        points_awarded=points,
        gas_awarded=gas_awarded,
        pb_set=pb_set,
    ))

    # Lifetime stats
    stats = await db.get(LifetimeStats, user.id)
    if stats:
        stats.total_runs_completed += 1

    await db.flush()
    return lootbox


async def _try_award_cosmetic(user_id: uuid.UUID, events: DailyRunEvents, db: AsyncSession) -> None:
    """10% chance of a cosmetic drop on ghost win."""
    from app.services.events import _roll

    drop_roll = _roll(user_id, events.date, "cosmetic_drop")
    if drop_roll >= 0.10:
        return

    # Pick a random cosmetic not already owned
    all_cosmetics = (await db.scalars(select(Cosmetic))).all()
    owned_ids = set(
        row for row in await db.scalars(
            select(CosmeticInventory.cosmetic_id).where(CosmeticInventory.user_id == user_id)
        )
    )
    available = [c for c in all_cosmetics if c.id not in owned_ids]
    if not available:
        return

    pick_roll = _roll(user_id, events.date, "cosmetic_pick")
    cosmetic = available[int(pick_roll * len(available)) % len(available)]
    db.add(CosmeticInventory(
        user_id=user_id,
        cosmetic_id=cosmetic.id,
        obtained_at=datetime.now(timezone.utc),
    ))


async def process_user_days(
    user_id: uuid.UUID,
    from_date: date,
    to_date: date,
    db: AsyncSession,
) -> CatchUpSummary:
    """
    Process each calendar day in [from_date, to_date] for user.
    Idempotent: already-processed days are skipped.
    Deterministic: event outcomes stored on first roll.
    Protected by PostgreSQL advisory lock per user.
    """
    # Advisory lock per user for the transaction duration (PostgreSQL only)
    dialect = db.bind.dialect.name if db.bind else ""
    if dialect == "postgresql":
        lock_id = int.from_bytes(user_id.bytes[:4], "big") & 0x7FFFFFFF
        await db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})

    user = await db.get(User, user_id, with_for_update=True)
    if not user:
        raise ValueError(f"User {user_id} not found")

    run, track = await _get_or_create_run(user, db)

    summary = CatchUpSummary()
    streak_at_start = user.streak

    for current_date in _date_range(from_date, to_date):
        # Skip already-processed days (idempotency)
        existing = await db.scalar(
            select(DailyProcessedDay).where(
                DailyProcessedDay.user_id == user_id,
                DailyProcessedDay.date == current_date,
            )
        )
        if existing:
            summary.days.append(SummaryDay(
                date=current_date,
                qualified=existing.qualified,
                gas_used=existing.gas_used,
                crashed=existing.crashed,
                segment_advanced=existing.segment_advanced,
                run_completed=existing.run_completed,
                stopwatch_delta=existing.stopwatch_delta,
            ))
            continue

        # Fetch activity for this day
        activity = await get_or_fetch_activity(user, current_date, db)

        qualified = activity.github_commit_count > 0 or (
            user.leetcode_validated and activity.lc_total_accepted > 0
        )

        day_record = DailyProcessedDay(
            user_id=user_id,
            date=current_date,
            run_id=run.id,
            qualified=qualified,
        )

        if not qualified:
            # Check momentum perk (absorb 1 crash at 10+ streak, once per run)
            momentum_active = await user_has_active_perk(user_id, "momentum", db)
            if momentum_active and user.streak >= 10 and not run.momentum_used:
                run.momentum_used = True
                qualified = True  # absorbed
                day_record.gas_used = True  # treated similarly to gas use
            elif user.gas > 0:
                user.gas -= 1
                day_record.gas_used = True
                qualified = True
                # Lifetime stats
                stats = await db.get(LifetimeStats, user_id)
                if stats:
                    stats.total_gas_used += 1
            else:
                # CRASH
                user.streak = 0
                run.segment_index = 0
                run.stopwatch_seconds = 0
                run.corner_saves = 0
                run.weather_penalties_taken = 0
                run.ghost_wins = 0
                run.momentum_used = False
                day_record.crashed = True

                stats = await db.get(LifetimeStats, user_id)
                if stats:
                    stats.total_crashes += 1

                db.add(day_record)
                summary.days.append(SummaryDay(
                    date=current_date, qualified=False, crashed=True
                ))
                summary.crashed = True
                summary.days_processed += 1
                await db.flush()
                continue

        # Advance segment
        run.segment_index += 1
        run.last_processed_date = current_date
        user.streak += 1
        if user.streak > user.longest_streak:
            user.longest_streak = user.streak
        day_record.segment_advanced = True

        # Lifetime stats
        stats = await db.get(LifetimeStats, user_id)
        if stats:
            stats.total_days_qualified += 1

        # Roll or fetch events
        events = await get_or_roll_events(
            user_id=user_id,
            event_date=current_date,
            run_id=run.id,
            segment_index=run.segment_index,
            has_leetcode=user.leetcode_validated,
            db=db,
        )

        # Compute stopwatch delta
        base_time = track.base_seconds_per_segment
        if await user_has_active_perk(user_id, "smooth_line", db):
            base_time = int(base_time * 0.95)
        delta = base_time

        # Corner challenge
        corner_completed = None
        if events.corner_type:
            corner_met = evaluate_requirement(events.corner_requirement, activity)
            events.corner_completed = corner_met
            corner_completed = corner_met
            if corner_met:
                save = events.corner_time_save_seconds or 0
                if await user_has_active_perk(user_id, "hairpin_specialist", db):
                    save = int(save * 1.08)
                delta -= save
                run.corner_saves += 1
                if stats:
                    stats.total_corner_saves += 1

        # Weather event
        weather_survived = None
        if events.weather_type:
            survived = evaluate_requirement(events.weather_requirement, activity)
            events.weather_survived = survived
            weather_survived = survived
            if not survived:
                penalty = events.weather_penalty_seconds or 0
                if await user_has_active_perk(user_id, "rain_tires", db):
                    penalty = int(penalty * 0.85)
                delta += penalty
                run.weather_penalties_taken += 1
            else:
                if stats:
                    stats.total_weather_survived += 1

        # Ghost/Rival event
        ghost_points = 0
        ghost_won = None
        if events.ghost_name:
            won = evaluate_requirement(events.ghost_requirement, activity)
            events.ghost_won = won
            ghost_won = won
            if won:
                run.ghost_wins += 1
                diff = events.ghost_difficulty or "easy"
                ghost_points = GHOST_POINTS.get(diff, 50)
                if await user_has_active_perk(user_id, "draft_master", db):
                    ghost_points = int(ghost_points * 1.10)
                user.total_points += ghost_points
                user.spendable_points += ghost_points
                summary.ghost_wins += 1
                if stats:
                    stats.total_ghost_wins += 1
                await _try_award_cosmetic(user_id, events, db)

        run.stopwatch_seconds = max(0, run.stopwatch_seconds + delta)
        day_record.stopwatch_delta = delta
        events.processed = True

        # Check run completion
        lootbox_awarded = False
        if run.segment_index >= track.length_days:
            await _complete_run(user, run, track, db)
            day_record.run_completed = True
            lootbox_awarded = True
            summary.run_completed = True
            summary.lootboxes_awarded += 1
            run, track = await _start_new_run(user, exclude_track_id=run.track_id, db=db)

        db.add(day_record)
        summary.days.append(SummaryDay(
            date=current_date,
            qualified=qualified,
            gas_used=day_record.gas_used,
            crashed=False,
            segment_advanced=True,
            run_completed=lootbox_awarded,
            stopwatch_delta=delta,
            corner_completed=corner_completed,
            weather_survived=weather_survived,
            ghost_won=ghost_won,
            ghost_points=ghost_points,
        ))
        summary.days_processed += 1
        summary.stopwatch_delta += delta
        if day_record.gas_used:
            summary.gas_used += 1

        await db.flush()

    summary.net_streak_change = user.streak - streak_at_start
    await db.commit()
    return summary
