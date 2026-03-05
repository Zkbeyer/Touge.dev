"""Tests for the core game loop: process_user_days."""
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import DailyProcessedDay
from app.models.run import Run
from app.models.stats import LifetimeStats
from app.models.user import User
from app.services.processor import process_user_days


def _make_activity(commits: int = 1, lc_total: int = 0):
    """Build a mock DailyActivity using SimpleNamespace to avoid ORM issues."""
    from types import SimpleNamespace
    return SimpleNamespace(
        github_commit_count=commits,
        lc_easy_accepted=0,
        lc_medium_accepted=0,
        lc_hard_accepted=0,
        lc_total_accepted=lc_total,
    )


@pytest.mark.asyncio
async def test_qualified_day_advances_segment(db, test_user, test_track):
    """A qualified day advances the segment and streak."""
    with (
        patch("app.services.processor.get_or_fetch_activity", new_callable=AsyncMock) as mock_activity,
        patch("app.services.processor.user_has_active_perk", new_callable=AsyncMock, return_value=False),
    ):
        mock_activity.return_value = _make_activity(commits=2)

        d = date(2026, 3, 1)
        summary = await process_user_days(test_user.id, d, d, db)

    assert summary.days_processed == 1
    assert not summary.crashed
    assert summary.net_streak_change == 1

    run = await db.scalar(select(Run).where(Run.user_id == test_user.id))
    assert run.segment_index == 1

    await db.refresh(test_user)
    assert test_user.streak == 1


@pytest.mark.asyncio
async def test_unqualified_day_with_gas_uses_gas(db, test_user, test_track):
    """Unqualified day with gas available uses gas and advances segment."""
    test_user.gas = 2
    await db.flush()

    with (
        patch("app.services.processor.get_or_fetch_activity", new_callable=AsyncMock) as mock_activity,
        patch("app.services.processor.user_has_active_perk", new_callable=AsyncMock, return_value=False),
    ):
        mock_activity.return_value = _make_activity(commits=0)

        d = date(2026, 3, 1)
        summary = await process_user_days(test_user.id, d, d, db)

    assert summary.gas_used == 1
    assert not summary.crashed
    assert summary.days[0].gas_used is True

    await db.refresh(test_user)
    assert test_user.gas == 1


@pytest.mark.asyncio
async def test_unqualified_day_no_gas_crashes(db, test_user, test_track):
    """Unqualified day with no gas causes a crash."""
    test_user.gas = 0
    test_user.streak = 5
    await db.flush()

    # First set up a run with some progress
    run = Run(
        user_id=test_user.id,
        track_id=test_track.id,
        start_date=date(2026, 2, 20),
        segment_index=5,
        stopwatch_seconds=200,
    )
    db.add(run)
    await db.flush()

    with (
        patch("app.services.processor.get_or_fetch_activity", new_callable=AsyncMock) as mock_activity,
        patch("app.services.processor.user_has_active_perk", new_callable=AsyncMock, return_value=False),
    ):
        mock_activity.return_value = _make_activity(commits=0)

        d = date(2026, 3, 1)
        summary = await process_user_days(test_user.id, d, d, db)

    assert summary.crashed is True
    assert summary.days[0].crashed is True

    await db.refresh(test_user)
    assert test_user.streak == 0

    await db.refresh(run)
    assert run.segment_index == 0
    assert run.stopwatch_seconds == 0


@pytest.mark.asyncio
async def test_idempotency(db, test_user, test_track):
    """Processing the same day twice is idempotent."""
    with (
        patch("app.services.processor.get_or_fetch_activity", new_callable=AsyncMock) as mock_activity,
        patch("app.services.processor.user_has_active_perk", new_callable=AsyncMock, return_value=False),
    ):
        mock_activity.return_value = _make_activity(commits=2)

        d = date(2026, 3, 1)
        summary1 = await process_user_days(test_user.id, d, d, db)
        summary2 = await process_user_days(test_user.id, d, d, db)

    # Second call should skip the already-processed day
    await db.refresh(test_user)
    assert test_user.streak == 1  # not 2


@pytest.mark.asyncio
async def test_run_completes_at_track_end(db, test_user, test_track):
    """Run completes when segment_index reaches track length."""
    # Set up a run at the second-to-last segment
    run = Run(
        user_id=test_user.id,
        track_id=test_track.id,
        start_date=date(2026, 2, 1),
        segment_index=test_track.length_days - 1,  # one away from completion
        stopwatch_seconds=100,
    )
    db.add(run)
    await db.flush()

    with (
        patch("app.services.processor.get_or_fetch_activity", new_callable=AsyncMock) as mock_activity,
        patch("app.services.processor.user_has_active_perk", new_callable=AsyncMock, return_value=False),
    ):
        mock_activity.return_value = _make_activity(commits=3)

        d = date(2026, 3, 1)
        summary = await process_user_days(test_user.id, d, d, db)

    assert summary.run_completed is True
    assert summary.lootboxes_awarded == 1

    # Old run should be complete
    await db.refresh(run)
    assert run.is_complete is True

    # New run should exist
    new_run = await db.scalar(
        select(Run).where(Run.user_id == test_user.id, Run.is_complete == False)
    )
    assert new_run is not None
    assert new_run.segment_index == 0


@pytest.mark.asyncio
async def test_multiple_days_catchup(db, test_user, test_track):
    """Multiple days are processed correctly in sequence."""
    with (
        patch("app.services.processor.get_or_fetch_activity", new_callable=AsyncMock) as mock_activity,
        patch("app.services.processor.user_has_active_perk", new_callable=AsyncMock, return_value=False),
    ):
        mock_activity.return_value = _make_activity(commits=2)

        from_date = date(2026, 3, 1)
        to_date = date(2026, 3, 3)
        summary = await process_user_days(test_user.id, from_date, to_date, db)

    assert summary.days_processed == 3
    assert summary.net_streak_change == 3

    await db.refresh(test_user)
    assert test_user.streak == 3

    run = await db.scalar(select(Run).where(Run.user_id == test_user.id))
    assert run.segment_index == 3
