import hashlib
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import DailyActivity
from app.models.event import DailyRunEvents

# Weather: independent random chance per day, cannot stack
WEATHER_CHANCE = 0.25  # 25% — lower than before so corner+weather combo is rare

CORNER_TYPES = ["sweeper", "chicane", "hairpin"]
CORNER_SAVES = {"sweeper": 10, "chicane": 18, "hairpin": 30}

WEATHER_TYPES = ["fog", "rain", "night_run"]
WEATHER_PENALTIES = {"fog": 15, "rain": 30, "night_run": 45}

# --- Ghost/rival feature removed (commented out, to be re-added later) ---
# GHOST_CHANCE = 0.30
# GHOST_DIFFICULTIES = ["easy", "medium", "hard"]
# GHOST_POINTS = {"easy": 50, "medium": 100, "hard": 200}


def _roll(identifier: str | uuid.UUID, event_date: date, event_type: str, salt: str = "v1") -> float:
    """Returns a stable float in [0.0, 1.0) for a given (identifier, date, event_type)."""
    key = f"{identifier}:{event_date.isoformat()}:{event_type}:{salt}"
    h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    return (h % 1_000_000) / 1_000_000.0


def _pick_by_roll(items: list, roll: float) -> str:
    """Pick item from list using roll value as index fraction."""
    return items[int(roll * len(items)) % len(items)]


def _generate_corner_requirement(corner_type: str, segment_index: int, has_leetcode: bool) -> dict:
    """Generate corner requirement scaled by difficulty tier (every 5 segments)."""
    tier = min(segment_index // 5, 3)
    lc_pool = has_leetcode

    if corner_type == "sweeper":
        # Easy: just need a commit
        return {"type": "commits", "count": 1}
    elif corner_type == "chicane":
        if tier >= 2 and lc_pool:
            return {"type": "lc_medium", "count": 1}
        return {"type": "commits", "count": 2 + tier}
    else:  # hairpin — hardest
        if tier >= 3 and lc_pool:
            return {"type": "lc_hard", "count": 1}
        if tier >= 1 and lc_pool:
            return {"type": "lc_medium", "count": 1}
        return {"type": "commits", "count": 3 + tier}


def _generate_weather_requirement(weather_type: str, has_leetcode: bool) -> dict:
    """Generate weather survival requirement."""
    if weather_type == "fog":
        return {"type": "commits", "count": 1}
    elif weather_type == "rain":
        return {"type": "commits_or_lc", "commits": 2, "lc": 1}
    else:  # night_run — hardest
        if has_leetcode:
            return {"type": "lc_any", "count": 1}
        return {"type": "commits", "count": 3}


def evaluate_requirement(req: dict | None, activity: DailyActivity) -> bool:
    """Returns True if daily activity satisfies the event requirement."""
    if req is None:
        return False
    match req["type"]:
        case "commits":
            return activity.github_commit_count >= req["count"]
        case "lc_easy":
            return activity.lc_easy_accepted >= req["count"]
        case "lc_medium":
            return activity.lc_medium_accepted >= req["count"]
        case "lc_hard":
            return activity.lc_hard_accepted >= req["count"]
        case "lc_any":
            return activity.lc_total_accepted >= req["count"]
        case "commits_or_lc":
            return (
                activity.github_commit_count >= req.get("commits", 1)
                or activity.lc_total_accepted >= req.get("lc", 1)
            )
        case _:
            return False


async def get_or_roll_events(
    user_id: uuid.UUID,
    event_date: date,
    run_id: uuid.UUID,
    segment_index: int,
    has_leetcode: bool,
    db: AsyncSession,
    segment_type: str | None = None,
) -> DailyRunEvents:
    """
    Returns existing event record (deterministic) or rolls new events for the day.

    segment_type: the type from the track's segment_layout (e.g. "hairpin", "sweeper", "chicane",
    "straight", or None). If "straight" or None, no corner event is created.
    Corner events are no longer probabilistic — they are always present on corner segments.
    Weather is still random (25% chance) and independent.
    """
    existing = await db.scalar(
        select(DailyRunEvents).where(
            DailyRunEvents.user_id == user_id,
            DailyRunEvents.date == event_date,
        )
    )
    if existing:
        return existing

    # Corner: determined entirely by track layout — no random roll
    corner_type = corner_req = corner_save = None
    if segment_type and segment_type != "straight":
        corner_type = segment_type  # sweeper / chicane / hairpin
        corner_req = _generate_corner_requirement(corner_type, segment_index, has_leetcode)
        corner_save = CORNER_SAVES[corner_type]

    # Weather: independent 25% random chance — cannot stack (one type per day max)
    weather_roll = _roll(user_id, event_date, "weather")
    weather_type = weather_req = weather_penalty = None
    if weather_roll < WEATHER_CHANCE:
        type_roll = _roll(user_id, event_date, "weather_type")
        weather_type = _pick_by_roll(WEATHER_TYPES, type_roll)
        weather_req = _generate_weather_requirement(weather_type, has_leetcode)
        weather_penalty = WEATHER_PENALTIES[weather_type]

    # --- Ghost/rival feature removed ---
    # ghost_roll = _roll(user_id, event_date, "ghost")
    # ... ghost logic commented out for now ...

    record = DailyRunEvents(
        user_id=user_id,
        date=event_date,
        run_id=run_id,
        segment_index=segment_index,
        corner_roll=None,      # no longer used — corner presence is layout-driven
        weather_roll=weather_roll,
        ghost_roll=None,       # ghost removed for now
        corner_type=corner_type,
        corner_requirement=corner_req,
        corner_time_save_seconds=corner_save,
        weather_type=weather_type,
        weather_requirement=weather_req,
        weather_penalty_seconds=weather_penalty,
        ghost_name=None,
        ghost_difficulty=None,
        ghost_requirement=None,
    )
    db.add(record)
    return record
