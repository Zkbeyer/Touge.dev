import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import DailyActivity
from app.models.event import DailyProcessedDay, DailyRunEvents
from app.models.run import CompletedRun, Run
from app.models.stats import LifetimeStats
from app.models.track import Track
from app.models.user import User
from app.services.activity import get_or_fetch_activity
from app.services.events import evaluate_requirement, get_or_roll_events

# --- Garage / lootbox / perk features disabled for now ---
# from app.models.car import CarOwnership, Perk
# from app.models.cosmetic import Cosmetic, CosmeticInventory
# from app.models.reward import Lootbox, PersonalBest
# from app.services.events import GHOST_POINTS
# from app.services.garage import user_has_active_perk
# from app.services.lootbox import pick_lootbox_tier
# BASE_GAS_CHANCE = 0.15

DIFFICULTY_ORDER = {"beginner": 1, "intermediate": 2, "expert": 3}


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
    # ghost_won: bool | None = None  # ghost removed
    # ghost_points: int = 0          # ghost removed


@dataclass
class CatchUpSummary:
    days: list[SummaryDay] = field(default_factory=list)
    days_processed: int = 0
    net_streak_change: int = 0
    gas_used: int = 0
    crashed: bool = False
    stopwatch_delta: int = 0
    # ghost_wins: int = 0            # ghost removed
    run_completed: bool = False
    # lootboxes_awarded: int = 0     # lootbox removed


@dataclass
class TodayChallenge:
    event_type: str
    corner_type: str | None = None
    weather_type: str | None = None
    # ghost_name: str | None = None      # ghost removed
    # ghost_difficulty: str | None = None # ghost removed
    requirement: dict | None = None
    current_value: int = 0
    met: bool = False
    time_save_seconds: int | None = None
    penalty_seconds: int | None = None


@dataclass
class TodayStatus:
    qualified: bool
    streak_applied: bool
    segment_advanced: bool
    has_challenges: bool
    all_challenges_met: bool
    challenges: list[TodayChallenge] = field(default_factory=list)


def _date_range(from_date: date, to_date: date):
    current = from_date
    while current <= to_date:
        yield current
        current += timedelta(days=1)


def _today_for_user(user: User) -> date:
    tz = ZoneInfo(user.timezone)
    return datetime.now(tz).date()


def _segment_type_for_index(track: Track, segment_index: int) -> str | None:
    """
    Returns the segment type ("straight", "sweeper", "chicane", "hairpin") at the
    given segment_index (1-based, post-increment). Layout is 0-based, so lookup at
    segment_index - 1.
    Returns None if no layout defined or index is out of range.
    """
    layout = track.segment_layout
    if not layout:
        return None
    idx = segment_index - 1
    if 0 <= idx < len(layout):
        return layout[idx].get("type", "straight")
    return "straight"


async def _complete_run(
    user: User, run: Run, track: Track, db: AsyncSession
) -> None:
    """Complete the current run. Lootbox/gas/PB features disabled for now."""
    now = datetime.now(timezone.utc)

    # --- Lootbox / gas / points disabled for now ---
    # score = _calculate_performance_score(run, track, user)
    # tier = pick_lootbox_tier(score)
    # points = score * 3
    # gas_roll = _roll(run.id, now.date(), "gas_drop")
    # gas_chance = BASE_GAS_CHANCE
    # gas_awarded = 1 if gas_roll < gas_chance else 0
    # user.gas += gas_awarded
    # user.total_points += points
    # user.spendable_points += points

    run.is_complete = True
    run.completed_at = now
    # run.lootbox_tier = tier

    db.add(CompletedRun(
        user_id=user.id,
        track_id=track.id,
        run_id=run.id,
        completed_at=now,
        total_seconds=run.stopwatch_seconds,
        corner_saves=run.corner_saves,
        weather_penalties_taken=run.weather_penalties_taken,
        ghost_wins=0,
        streak_at_completion=user.streak,
        lootbox_tier="none",
        points_awarded=0,
        gas_awarded=0,
        pb_set=False,
    ))

    stats = await db.get(LifetimeStats, user.id)
    if stats:
        stats.total_runs_completed += 1

    await db.flush()


async def get_or_create_run(user: User, db: AsyncSession) -> tuple[Run, Track]:
    """Gets user's active run or creates a new one on a beginner track."""
    run = await db.scalar(
        select(Run).where(Run.user_id == user.id, Run.is_complete == False)
    )
    if run:
        track = await db.get(Track, run.track_id)
        return run, track

    # Pick first active beginner track by slug (deterministic)
    track = await db.scalar(
        select(Track)
        .where(Track.is_active == True, Track.difficulty == "beginner")
        .order_by(Track.slug)
        .limit(1)
    )
    if not track:
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

    tracks = (await db.scalars(query)).all()
    if tracks:
        tracks = sorted(tracks, key=lambda t: (DIFFICULTY_ORDER.get(t.difficulty, 99), t.slug))
        track = tracks[0]
    else:
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


def _get_activity_value(activity: DailyActivity, requirement: dict | None) -> int:
    """Returns the current numeric value for a requirement type (for display)."""
    if requirement is None or activity is None:
        return 0
    req_type = requirement.get("type", "")
    if req_type == "commits":
        return activity.github_commit_count
    elif req_type == "lc_easy":
        return activity.lc_easy_accepted
    elif req_type == "lc_medium":
        return activity.lc_medium_accepted
    elif req_type == "lc_hard":
        return activity.lc_hard_accepted
    elif req_type == "lc_any":
        return activity.lc_total_accepted
    elif req_type == "commits_or_lc":
        return max(activity.github_commit_count, activity.lc_total_accepted)
    elif req_type == "commits_and_lc":
        return activity.github_commit_count  # shows commit progress; lc tracked via met flag
    elif req_type == "repos":
        return activity.github_repo_count
    return 0


def _build_challenge_list(events: DailyRunEvents, activity: DailyActivity) -> list[TodayChallenge]:
    """Build TodayChallenge list from rolled events and current activity."""
    challenges = []
    if events.corner_type:
        met = evaluate_requirement(events.corner_requirement, activity)
        challenges.append(TodayChallenge(
            event_type="corner",
            corner_type=events.corner_type,
            requirement=events.corner_requirement,
            current_value=_get_activity_value(activity, events.corner_requirement),
            met=met,
            time_save_seconds=events.corner_time_save_seconds,
        ))
    if events.weather_type:
        met = evaluate_requirement(events.weather_requirement, activity)
        challenges.append(TodayChallenge(
            event_type="weather",
            weather_type=events.weather_type,
            requirement=events.weather_requirement,
            current_value=_get_activity_value(activity, events.weather_requirement),
            met=met,
            penalty_seconds=events.weather_penalty_seconds,
        ))
    # --- Ghost challenge removed ---
    # if events.ghost_name: ...
    return challenges


async def _finalize_today_segment(
    user: User,
    run: Run,
    track: Track,
    events: DailyRunEvents,
    activity: DailyActivity,
    today: date,
    processed: DailyProcessedDay | None,
    db: AsyncSession,
) -> TodayStatus:
    """
    Advance today's segment and apply event outcomes.
    processed=None means create a new DailyProcessedDay; otherwise update existing.
    """
    base_time = track.base_seconds_per_segment
    # Perk: smooth_line disabled
    # if await user_has_active_perk(user.id, "smooth_line", db):
    #     base_time = int(base_time * 0.95)
    delta = base_time

    stats = await db.get(LifetimeStats, user.id)
    challenges = []

    # Corner
    if events.corner_type:
        corner_met = evaluate_requirement(events.corner_requirement, activity)
        events.corner_completed = corner_met
        challenges.append(TodayChallenge(
            event_type="corner",
            corner_type=events.corner_type,
            requirement=events.corner_requirement,
            current_value=_get_activity_value(activity, events.corner_requirement),
            met=corner_met,
            time_save_seconds=events.corner_time_save_seconds,
        ))
        if corner_met:
            save = events.corner_time_save_seconds or 0
            # Perk: hairpin_specialist disabled
            # if await user_has_active_perk(user.id, "hairpin_specialist", db):
            #     save = int(save * 1.08)
            delta -= save
            run.corner_saves += 1
            if stats:
                stats.total_corner_saves += 1

    # Weather
    if events.weather_type:
        survived = evaluate_requirement(events.weather_requirement, activity)
        events.weather_survived = survived
        challenges.append(TodayChallenge(
            event_type="weather",
            weather_type=events.weather_type,
            requirement=events.weather_requirement,
            current_value=_get_activity_value(activity, events.weather_requirement),
            met=survived,
            penalty_seconds=events.weather_penalty_seconds,
        ))
        if not survived:
            penalty = events.weather_penalty_seconds or 0
            # Perk: rain_tires disabled
            # if await user_has_active_perk(user.id, "rain_tires", db):
            #     penalty = int(penalty * 0.85)
            delta += penalty
            run.weather_penalties_taken += 1
        else:
            if stats:
                stats.total_weather_survived += 1

    # --- Ghost removed ---
    # if events.ghost_name: ...

    run.segment_index += 1
    run.stopwatch_seconds = max(0, run.stopwatch_seconds + delta)
    run.last_processed_date = today
    events.processed = True

    if processed is None:
        processed = DailyProcessedDay(
            user_id=user.id,
            date=today,
            run_id=run.id,
            qualified=True,
            segment_advanced=True,
            stopwatch_delta=delta,
        )
        db.add(processed)
    else:
        processed.segment_advanced = True
        processed.stopwatch_delta = delta

    # Check run completion
    if run.segment_index >= track.length_days:
        await _complete_run(user, run, track, db)
        processed.run_completed = True
        await _start_new_run(user, exclude_track_id=run.track_id, db=db)

    await db.flush()
    await db.commit()

    has_challenges = bool(challenges)
    all_met = all(c.met for c in challenges) if challenges else True
    return TodayStatus(
        qualified=True,
        streak_applied=True,
        segment_advanced=True,
        has_challenges=has_challenges,
        all_challenges_met=all_met,
        challenges=challenges,
    )


async def get_today_status(user: User, db: AsyncSession) -> TodayStatus:
    """Read-only: returns the current today processing status from DB state."""
    today = _today_for_user(user)

    processed = await db.scalar(
        select(DailyProcessedDay).where(
            DailyProcessedDay.user_id == user.id,
            DailyProcessedDay.date == today,
        )
    )

    if not processed or not processed.qualified:
        return TodayStatus(
            qualified=False,
            streak_applied=False,
            segment_advanced=False,
            has_challenges=False,
            all_challenges_met=False,
        )

    events = await db.scalar(
        select(DailyRunEvents).where(
            DailyRunEvents.user_id == user.id,
            DailyRunEvents.date == today,
        )
    )

    activity = await get_or_fetch_activity(user, today, db)

    if not events:
        return TodayStatus(
            qualified=True,
            streak_applied=True,
            segment_advanced=processed.segment_advanced,
            has_challenges=False,
            all_challenges_met=True,
        )

    challenges = _build_challenge_list(events, activity)
    has_challenges = bool(challenges)
    all_met = all(c.met for c in challenges) if challenges else True
    return TodayStatus(
        qualified=True,
        streak_applied=True,
        segment_advanced=processed.segment_advanced,
        has_challenges=has_challenges,
        all_challenges_met=all_met,
        challenges=challenges,
    )


async def process_today_phase1(user: User, db: AsyncSession) -> TodayStatus:
    """
    Phase 1: qualify today — increment streak and roll events if user has activity.
    Called by GET /run. Commits if new work is done.
    If no event challenges exist, immediately advances the segment (Phase 2 inline).
    """
    today = _today_for_user(user)

    activity = await get_or_fetch_activity(user, today, db, force_refetch=True)

    qualified = activity.github_commit_count > 0 or (
        user.leetcode_validated and activity.lc_total_accepted > 0
    )

    if not qualified:
        return TodayStatus(
            qualified=False,
            streak_applied=False,
            segment_advanced=False,
            has_challenges=False,
            all_challenges_met=False,
        )

    # Check if Phase 1 already ran for today
    existing = await db.scalar(
        select(DailyProcessedDay).where(
            DailyProcessedDay.user_id == user.id,
            DailyProcessedDay.date == today,
        )
    )
    if existing:
        return await get_today_status(user, db)

    # --- Fresh Phase 1 ---
    user.streak += 1
    if user.streak > user.longest_streak:
        user.longest_streak = user.streak

    stats = await db.get(LifetimeStats, user.id)
    if stats:
        stats.total_days_qualified += 1

    run, track = await get_or_create_run(user, db)

    # Determine segment type from track layout (next segment = current index + 1, 1-based)
    next_seg_idx = run.segment_index + 1
    segment_type = _segment_type_for_index(track, next_seg_idx)

    # Roll events for the upcoming segment
    events = await get_or_roll_events(
        user_id=user.id,
        event_date=today,
        run_id=run.id,
        segment_index=next_seg_idx,
        has_leetcode=user.leetcode_validated,
        db=db,
        segment_type=segment_type,
    )
    await db.flush()

    has_challenges = bool(events.corner_type or events.weather_type)

    if not has_challenges:
        # No challenges — finalize segment immediately
        return await _finalize_today_segment(user, run, track, events, activity, today, None, db)

    # Write pending DailyProcessedDay (segment_advanced=False)
    day_record = DailyProcessedDay(
        user_id=user.id,
        date=today,
        run_id=run.id,
        qualified=True,
        segment_advanced=False,
    )
    db.add(day_record)
    await db.flush()
    await db.commit()

    challenges = _build_challenge_list(events, activity)
    all_met = all(c.met for c in challenges) if challenges else True
    return TodayStatus(
        qualified=True,
        streak_applied=True,
        segment_advanced=False,
        has_challenges=True,
        all_challenges_met=all_met,
        challenges=challenges,
    )


async def process_today_phase2(
    user: User, db: AsyncSession, force_finalize: bool = False
) -> TodayStatus:
    """
    Phase 2: resolve today's segment — advance segment if all challenges met (or force_finalize).
    Called by POST /run/process. Also called by webhook/test with force_finalize=True.
    """
    today = _today_for_user(user)

    processed = await db.scalar(
        select(DailyProcessedDay).where(
            DailyProcessedDay.user_id == user.id,
            DailyProcessedDay.date == today,
        )
    )

    if not processed:
        # Phase 1 hasn't run — run it first
        status = await process_today_phase1(user, db)
        if not status.qualified or status.segment_advanced:
            return status
        await db.refresh(user)
        processed = await db.scalar(
            select(DailyProcessedDay).where(
                DailyProcessedDay.user_id == user.id,
                DailyProcessedDay.date == today,
            )
        )
        if not processed or processed.segment_advanced:
            return status

    if not processed.qualified:
        return TodayStatus(
            qualified=False,
            streak_applied=False,
            segment_advanced=False,
            has_challenges=False,
            all_challenges_met=False,
        )

    if processed.segment_advanced:
        return await get_today_status(user, db)

    # Re-fetch activity and events
    activity = await get_or_fetch_activity(user, today, db, force_refetch=True)
    events = await db.scalar(
        select(DailyRunEvents).where(
            DailyRunEvents.user_id == user.id,
            DailyRunEvents.date == today,
        )
    )

    challenges = _build_challenge_list(events, activity) if events else []
    all_met = all(c.met for c in challenges) if challenges else True

    if not all_met and not force_finalize:
        return TodayStatus(
            qualified=True,
            streak_applied=True,
            segment_advanced=False,
            has_challenges=bool(challenges),
            all_challenges_met=False,
            challenges=challenges,
        )

    # Finalize: advance segment
    run = await db.scalar(select(Run).where(Run.id == processed.run_id))
    track = await db.get(Track, run.track_id)
    return await _finalize_today_segment(user, run, track, events, activity, today, processed, db)


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
    Handles segment_advanced=False records (Phase 1 ran but day ended) by force-finalizing.
    """
    dialect = db.bind.dialect.name if db.bind else ""
    if dialect == "postgresql":
        lock_id = int.from_bytes(user_id.bytes[:4], "big") & 0x7FFFFFFF
        await db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})

    user = await db.get(User, user_id, with_for_update=True)
    if not user:
        raise ValueError(f"User {user_id} not found")

    run, track = await get_or_create_run(user, db)

    summary = CatchUpSummary()
    streak_at_start = user.streak

    for current_date in _date_range(from_date, to_date):
        existing = await db.scalar(
            select(DailyProcessedDay).where(
                DailyProcessedDay.user_id == user_id,
                DailyProcessedDay.date == current_date,
            )
        )

        if existing and existing.segment_advanced:
            # Fully done — skip
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

        if existing and not existing.segment_advanced:
            # Phase 1 ran but day ended before segment advanced — force-finalize.
            if existing.crashed:
                summary.days.append(SummaryDay(date=current_date, qualified=False, crashed=True))
                continue

            activity = await get_or_fetch_activity(user, current_date, db)
            events = await db.scalar(
                select(DailyRunEvents).where(
                    DailyRunEvents.user_id == user_id,
                    DailyRunEvents.date == current_date,
                )
            )

            base_time = track.base_seconds_per_segment
            delta = base_time

            stats = await db.get(LifetimeStats, user_id)
            corner_completed = weather_survived = None

            if events:
                if events.corner_type:
                    corner_met = evaluate_requirement(events.corner_requirement, activity)
                    events.corner_completed = corner_met
                    corner_completed = corner_met
                    if corner_met:
                        save = events.corner_time_save_seconds or 0
                        delta -= save
                        run.corner_saves += 1
                        if stats:
                            stats.total_corner_saves += 1

                if events.weather_type:
                    survived = evaluate_requirement(events.weather_requirement, activity)
                    events.weather_survived = survived
                    weather_survived = survived
                    if not survived:
                        penalty = events.weather_penalty_seconds or 0
                        delta += penalty
                        run.weather_penalties_taken += 1
                    else:
                        if stats:
                            stats.total_weather_survived += 1

                # --- Ghost removed ---
                events.processed = True

            run.segment_index += 1
            run.stopwatch_seconds = max(0, run.stopwatch_seconds + delta)
            run.last_processed_date = current_date
            existing.segment_advanced = True
            existing.stopwatch_delta = delta

            run_completed = False
            if run.segment_index >= track.length_days:
                await _complete_run(user, run, track, db)
                existing.run_completed = True
                run_completed = True
                summary.run_completed = True
                run, track = await _start_new_run(user, exclude_track_id=run.track_id, db=db)

            summary.days.append(SummaryDay(
                date=current_date,
                qualified=True,
                gas_used=existing.gas_used,
                crashed=False,
                segment_advanced=True,
                run_completed=run_completed,
                stopwatch_delta=delta,
                corner_completed=corner_completed,
                weather_survived=weather_survived,
            ))
            summary.days_processed += 1
            summary.stopwatch_delta += delta
            if existing.gas_used:
                summary.gas_used += 1

            await db.flush()
            continue

        # --- Fresh day (no existing record) ---
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
            # Momentum perk disabled
            # if momentum_active and ...: ...
            if user.gas > 0:
                user.gas -= 1
                day_record.gas_used = True
                qualified = True
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

        stats = await db.get(LifetimeStats, user_id)
        if stats:
            stats.total_days_qualified += 1

        # Determine segment type from layout (segment_index is already incremented, 1-based)
        segment_type = _segment_type_for_index(track, run.segment_index)

        # Roll or fetch events
        events = await get_or_roll_events(
            user_id=user_id,
            event_date=current_date,
            run_id=run.id,
            segment_index=run.segment_index,
            has_leetcode=user.leetcode_validated,
            db=db,
            segment_type=segment_type,
        )

        # Compute stopwatch delta
        base_time = track.base_seconds_per_segment
        delta = base_time

        # Corner challenge
        corner_completed = None
        if events.corner_type:
            corner_met = evaluate_requirement(events.corner_requirement, activity)
            events.corner_completed = corner_met
            corner_completed = corner_met
            if corner_met:
                save = events.corner_time_save_seconds or 0
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
                delta += penalty
                run.weather_penalties_taken += 1
            else:
                if stats:
                    stats.total_weather_survived += 1

        # --- Ghost removed ---

        run.stopwatch_seconds = max(0, run.stopwatch_seconds + delta)
        day_record.stopwatch_delta = delta
        events.processed = True

        # Check run completion
        run_completed = False
        if run.segment_index >= track.length_days:
            await _complete_run(user, run, track, db)
            day_record.run_completed = True
            run_completed = True
            summary.run_completed = True
            run, track = await _start_new_run(user, exclude_track_id=run.track_id, db=db)

        db.add(day_record)
        summary.days.append(SummaryDay(
            date=current_date,
            qualified=qualified,
            gas_used=day_record.gas_used,
            crashed=False,
            segment_advanced=True,
            run_completed=run_completed,
            stopwatch_delta=delta,
            corner_completed=corner_completed,
            weather_survived=weather_survived,
        ))
        summary.days_processed += 1
        summary.stopwatch_delta += delta
        if day_record.gas_used:
            summary.gas_used += 1

        await db.flush()

    summary.net_streak_change = user.streak - streak_at_start
    await db.commit()
    return summary
