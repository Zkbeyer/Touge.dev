"""Tests for deterministic event rolling."""
import uuid
from datetime import date

import pytest

from app.services.events import _roll, evaluate_requirement, get_or_roll_events
from app.models.activity import DailyActivity
from app.models.run import Run
from app.models.track import Track


def test_roll_determinism():
    """Same inputs always produce same output."""
    uid = uuid.uuid4()
    d = date(2026, 3, 1)
    r1 = _roll(uid, d, "corner")
    r2 = _roll(uid, d, "corner")
    assert r1 == r2


def test_roll_range():
    """Roll is always in [0.0, 1.0)."""
    uid = uuid.uuid4()
    for month in range(1, 13):
        r = _roll(uid, date(2026, month, 1), "corner")
        assert 0.0 <= r < 1.0


def test_roll_uniqueness():
    """Different event types produce different rolls for same user/date."""
    uid = uuid.uuid4()
    d = date(2026, 3, 1)
    corner = _roll(uid, d, "corner")
    weather = _roll(uid, d, "weather")
    ghost = _roll(uid, d, "ghost")
    # Highly unlikely all three are equal
    assert len({corner, weather, ghost}) > 1


def test_roll_different_users():
    """Different users get different rolls on same date."""
    uid1, uid2 = uuid.uuid4(), uuid.uuid4()
    d = date(2026, 3, 1)
    assert _roll(uid1, d, "corner") != _roll(uid2, d, "corner")


def test_evaluate_requirement_commits():
    activity = DailyActivity(
        user_id=uuid.uuid4(),
        date=date(2026, 3, 1),
        github_commit_count=3,
        lc_total_accepted=0,
    )
    assert evaluate_requirement({"type": "commits", "count": 3}, activity) is True
    assert evaluate_requirement({"type": "commits", "count": 4}, activity) is False


def test_evaluate_requirement_lc_medium():
    activity = DailyActivity(
        user_id=uuid.uuid4(),
        date=date(2026, 3, 1),
        github_commit_count=0,
        lc_easy_accepted=1,
        lc_medium_accepted=2,
        lc_hard_accepted=0,
        lc_total_accepted=3,
    )
    assert evaluate_requirement({"type": "lc_medium", "count": 1}, activity) is True
    assert evaluate_requirement({"type": "lc_hard", "count": 1}, activity) is False


def test_evaluate_requirement_commits_or_lc():
    activity = DailyActivity(
        user_id=uuid.uuid4(),
        date=date(2026, 3, 1),
        github_commit_count=2,
        lc_total_accepted=0,
    )
    req = {"type": "commits_or_lc", "commits": 2, "lc": 1}
    assert evaluate_requirement(req, activity) is True

    activity2 = DailyActivity(
        user_id=uuid.uuid4(),
        date=date(2026, 3, 1),
        github_commit_count=0,
        lc_total_accepted=1,
    )
    assert evaluate_requirement(req, activity2) is True

    activity3 = DailyActivity(
        user_id=uuid.uuid4(),
        date=date(2026, 3, 1),
        github_commit_count=1,
        lc_total_accepted=0,
    )
    assert evaluate_requirement(req, activity3) is False


def test_evaluate_requirement_none():
    activity = DailyActivity(
        user_id=uuid.uuid4(),
        date=date(2026, 3, 1),
        github_commit_count=5,
    )
    assert evaluate_requirement(None, activity) is False


@pytest.mark.asyncio
async def test_get_or_roll_events_idempotent(db, test_user, test_track):
    """Rolling events twice returns the same record."""
    run = Run(
        user_id=test_user.id,
        track_id=test_track.id,
        start_date=date(2026, 3, 1),
    )
    db.add(run)
    await db.flush()

    d = date(2026, 3, 1)
    events1 = await get_or_roll_events(test_user.id, d, run.id, 1, False, db)
    await db.flush()
    events2 = await get_or_roll_events(test_user.id, d, run.id, 1, False, db)

    assert events1.id == events2.id
    assert events1.corner_roll == events2.corner_roll
    assert events1.weather_roll == events2.weather_roll
    assert events1.ghost_roll == events2.ghost_roll


@pytest.mark.asyncio
async def test_get_or_roll_events_probabilities(db, test_user, test_track):
    """Events respect probability thresholds."""
    from app.services.events import CORNER_CHANCE, WEATHER_CHANCE, GHOST_CHANCE

    run = Run(
        user_id=test_user.id,
        track_id=test_track.id,
        start_date=date(2026, 3, 1),
    )
    db.add(run)
    await db.flush()

    d = date(2026, 3, 1)
    events = await get_or_roll_events(test_user.id, d, run.id, 1, False, db)

    if events.corner_roll < CORNER_CHANCE:
        assert events.corner_type is not None
    else:
        assert events.corner_type is None

    if events.weather_roll < WEATHER_CHANCE:
        assert events.weather_type is not None
    else:
        assert events.weather_type is None

    if events.ghost_roll < GHOST_CHANCE:
        assert events.ghost_name is not None
    else:
        assert events.ghost_name is None
