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


# ---------------------------------------------------------------------------
# Challenge pools
# Each entry has metadata fields (min_tier, requires_lc) stripped before
# storing in DB. The label field is kept in the stored requirement dict.
# ---------------------------------------------------------------------------

CORNER_CHALLENGES: dict[str, list[dict]] = {
    "sweeper": [
        {"min_tier": 0, "requires_lc": False, "type": "commits", "count": 2, "label": "Push 2 commits"},
        {"min_tier": 0, "requires_lc": False, "type": "commits", "count": 3, "label": "Push 3 commits"},
        {"min_tier": 0, "requires_lc": False, "type": "repos",   "count": 2, "label": "Commit to 2 repos"},
        {"min_tier": 0, "requires_lc": True,  "type": "lc_easy",  "count": 1, "label": "Solve 1 easy problem"},
        {"min_tier": 0, "requires_lc": True,  "type": "lc_any",   "count": 1, "label": "Solve 1 LC problem"},
        {"min_tier": 1, "requires_lc": False, "type": "commits", "count": 4, "label": "Push 4 commits"},
        {"min_tier": 1, "requires_lc": False, "type": "repos",   "count": 2, "label": "Commit to 2 repos"},
        {"min_tier": 1, "requires_lc": True,  "type": "lc_easy",  "count": 2, "label": "Solve 2 easy problems"},
        {"min_tier": 1, "requires_lc": True,  "type": "lc_medium", "count": 1, "label": "Solve 1 medium problem"},
        {"min_tier": 2, "requires_lc": False, "type": "commits", "count": 5, "label": "Push 5 commits"},
        {"min_tier": 2, "requires_lc": False, "type": "repos",   "count": 3, "label": "Commit to 3 repos"},
        {"min_tier": 2, "requires_lc": True,  "type": "lc_medium", "count": 1, "label": "Solve 1 medium problem"},
        {"min_tier": 2, "requires_lc": True,  "type": "commits_and_lc", "commits": 3, "lc": 1, "label": "3 commits and 1 LC problem"},
    ],
    "chicane": [
        {"min_tier": 0, "requires_lc": False, "type": "commits", "count": 3, "label": "Push 3 commits"},
        {"min_tier": 0, "requires_lc": False, "type": "repos",   "count": 2, "label": "Commit to 2 repos"},
        {"min_tier": 0, "requires_lc": True,  "type": "lc_easy",  "count": 1, "label": "Solve 1 easy problem"},
        {"min_tier": 0, "requires_lc": True,  "type": "lc_easy",  "count": 2, "label": "Solve 2 easy problems"},
        {"min_tier": 1, "requires_lc": False, "type": "commits", "count": 4, "label": "Push 4 commits"},
        {"min_tier": 1, "requires_lc": False, "type": "repos",   "count": 2, "label": "Commit to 2 repos"},
        {"min_tier": 1, "requires_lc": True,  "type": "lc_medium", "count": 1, "label": "Solve 1 medium problem"},
        {"min_tier": 1, "requires_lc": True,  "type": "commits_and_lc", "commits": 2, "lc": 1, "label": "2 commits and 1 LC problem"},
        {"min_tier": 2, "requires_lc": False, "type": "commits", "count": 5, "label": "Push 5 commits"},
        {"min_tier": 2, "requires_lc": False, "type": "repos",   "count": 3, "label": "Commit to 3 repos"},
        {"min_tier": 2, "requires_lc": True,  "type": "lc_medium", "count": 2, "label": "Solve 2 medium problems"},
        {"min_tier": 2, "requires_lc": True,  "type": "commits_and_lc", "commits": 3, "lc": 1, "label": "3 commits and 1 LC problem"},
        {"min_tier": 3, "requires_lc": False, "type": "commits", "count": 6, "label": "Push 6 commits"},
        {"min_tier": 3, "requires_lc": True,  "type": "lc_hard",  "count": 1, "label": "Solve 1 hard problem"},
        {"min_tier": 3, "requires_lc": True,  "type": "commits_and_lc", "commits": 2, "lc": 2, "label": "2 commits and 2 LC problems"},
    ],
    "hairpin": [
        {"min_tier": 0, "requires_lc": False, "type": "commits", "count": 4, "label": "Push 4 commits"},
        {"min_tier": 0, "requires_lc": False, "type": "repos",   "count": 2, "label": "Commit to 2 repos"},
        {"min_tier": 0, "requires_lc": True,  "type": "lc_medium", "count": 1, "label": "Solve 1 medium problem"},
        {"min_tier": 0, "requires_lc": True,  "type": "commits_and_lc", "commits": 2, "lc": 1, "label": "2 commits and 1 LC problem"},
        {"min_tier": 1, "requires_lc": False, "type": "commits", "count": 5, "label": "Push 5 commits"},
        {"min_tier": 1, "requires_lc": False, "type": "repos",   "count": 3, "label": "Commit to 3 repos"},
        {"min_tier": 1, "requires_lc": True,  "type": "lc_medium", "count": 2, "label": "Solve 2 medium problems"},
        {"min_tier": 1, "requires_lc": True,  "type": "commits_and_lc", "commits": 3, "lc": 1, "label": "3 commits and 1 LC problem"},
        {"min_tier": 2, "requires_lc": False, "type": "commits", "count": 6, "label": "Push 6 commits"},
        {"min_tier": 2, "requires_lc": False, "type": "repos",   "count": 3, "label": "Commit to 3 repos"},
        {"min_tier": 2, "requires_lc": True,  "type": "lc_hard",  "count": 1, "label": "Solve 1 hard problem"},
        {"min_tier": 2, "requires_lc": True,  "type": "lc_medium", "count": 3, "label": "Solve 3 medium problems"},
        {"min_tier": 3, "requires_lc": False, "type": "commits", "count": 8, "label": "Push 8 commits"},
        {"min_tier": 3, "requires_lc": True,  "type": "lc_hard",  "count": 2, "label": "Solve 2 hard problems"},
        {"min_tier": 3, "requires_lc": True,  "type": "commits_and_lc", "commits": 4, "lc": 2, "label": "4 commits and 2 LC problems"},
    ],
}

WEATHER_CHALLENGES: dict[str, list[dict]] = {
    "fog": [
        {"requires_lc": False, "type": "commits", "count": 2, "label": "Push 2 commits"},
        {"requires_lc": False, "type": "commits", "count": 3, "label": "Push 3 commits"},
        {"requires_lc": False, "type": "repos",   "count": 2, "label": "Commit to 2 repos"},
        {"requires_lc": True,  "type": "lc_easy",  "count": 1, "label": "Solve 1 easy problem"},
        {"requires_lc": True,  "type": "lc_any",   "count": 1, "label": "Solve 1 LC problem"},
    ],
    "rain": [
        {"requires_lc": False, "type": "commits", "count": 3, "label": "Push 3 commits"},
        {"requires_lc": False, "type": "commits", "count": 4, "label": "Push 4 commits"},
        {"requires_lc": False, "type": "repos",   "count": 2, "label": "Commit to 2 repos"},
        {"requires_lc": True,  "type": "lc_easy",  "count": 2, "label": "Solve 2 easy problems"},
        {"requires_lc": True,  "type": "lc_medium", "count": 1, "label": "Solve 1 medium problem"},
        {"requires_lc": True,  "type": "commits_and_lc", "commits": 2, "lc": 1, "label": "2 commits and 1 LC problem"},
    ],
    "night_run": [
        {"requires_lc": False, "type": "commits", "count": 4, "label": "Push 4 commits"},
        {"requires_lc": False, "type": "commits", "count": 5, "label": "Push 5 commits"},
        {"requires_lc": False, "type": "repos",   "count": 3, "label": "Commit to 3 repos"},
        {"requires_lc": True,  "type": "lc_any",   "count": 2, "label": "Solve 2 LC problems"},
        {"requires_lc": True,  "type": "lc_medium", "count": 1, "label": "Solve 1 medium problem"},
        {"requires_lc": True,  "type": "lc_hard",  "count": 1, "label": "Solve 1 hard problem"},
        {"requires_lc": True,  "type": "commits_and_lc", "commits": 2, "lc": 1, "label": "2 commits and 1 LC problem"},
    ],
}

_STRIP_KEYS = frozenset(("min_tier", "requires_lc"))


def _roll(identifier: str | uuid.UUID, event_date: date, event_type: str, salt: str = "v1") -> float:
    """Returns a stable float in [0.0, 1.0) for a given (identifier, date, event_type)."""
    key = f"{identifier}:{event_date.isoformat()}:{event_type}:{salt}"
    h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    return (h % 1_000_000) / 1_000_000.0


def _pick_by_roll(items: list, roll: float) -> str:
    """Pick item from list using roll value as index fraction."""
    return items[int(roll * len(items)) % len(items)]


def _pick_corner_challenge(
    corner_type: str, segment_index: int, has_leetcode: bool, roll: float
) -> dict:
    tier = min(segment_index // 5, 3)
    pool = [
        c for c in CORNER_CHALLENGES[corner_type]
        if c["min_tier"] <= tier and (not c["requires_lc"] or has_leetcode)
    ]
    if not pool:
        return {"type": "commits", "count": 2, "label": "Push 2 commits"}
    chosen = pool[int(roll * len(pool)) % len(pool)]
    return {k: v for k, v in chosen.items() if k not in _STRIP_KEYS}


def _pick_weather_challenge(weather_type: str, has_leetcode: bool, roll: float) -> dict:
    pool = [
        c for c in WEATHER_CHALLENGES[weather_type]
        if not c["requires_lc"] or has_leetcode
    ]
    if not pool:
        return {"type": "commits", "count": 2, "label": "Push 2 commits"}
    chosen = pool[int(roll * len(pool)) % len(pool)]
    return {k: v for k, v in chosen.items() if k not in _STRIP_KEYS}


# Backward-compat aliases (used by test_helpers force-weather endpoint)
def _generate_corner_requirement(corner_type: str, segment_index: int, has_leetcode: bool) -> dict:
    return _pick_corner_challenge(corner_type, segment_index, has_leetcode, roll=0.0)


def _generate_weather_requirement(weather_type: str, has_leetcode: bool) -> dict:
    return _pick_weather_challenge(weather_type, has_leetcode, roll=0.0)


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
        case "commits_and_lc":
            return (
                activity.github_commit_count >= req.get("commits", 1)
                and activity.lc_total_accepted >= req.get("lc", 1)
            )
        case "repos":
            return activity.github_repo_count >= req["count"]
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

    # Deterministic challenge-pick rolls
    corner_pick_roll = _roll(user_id, event_date, "corner_challenge_pick")
    weather_pick_roll = _roll(user_id, event_date, "weather_challenge_pick")

    # Corner: determined entirely by track layout — no random roll
    corner_type = corner_req = corner_save = None
    if segment_type and segment_type != "straight":
        corner_type = segment_type  # sweeper / chicane / hairpin
        corner_req = _pick_corner_challenge(corner_type, segment_index, has_leetcode, corner_pick_roll)
        corner_save = CORNER_SAVES[corner_type]

    # Weather: independent 25% random chance — cannot stack (one type per day max)
    weather_roll = _roll(user_id, event_date, "weather")
    weather_type = weather_req = weather_penalty = None
    if weather_roll < WEATHER_CHANCE:
        type_roll = _roll(user_id, event_date, "weather_type")
        weather_type = _pick_by_roll(WEATHER_TYPES, type_roll)
        weather_req = _pick_weather_challenge(weather_type, has_leetcode, weather_pick_roll)
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
