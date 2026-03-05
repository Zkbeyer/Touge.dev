from datetime import datetime

from pydantic import BaseModel


class PersonalBestResponse(BaseModel):
    track_id: str
    track_name: str
    track_slug: str
    best_seconds: int
    best_formatted: str
    set_at: datetime


class LifetimeStatsResponse(BaseModel):
    total_runs_completed: int
    total_days_qualified: int
    total_gas_used: int
    total_crashes: int
    total_corner_saves: int
    total_weather_survived: int
    total_ghost_wins: int
    total_lootboxes_opened: int
    total_cars_owned: int


class ProfileResponse(BaseModel):
    id: str
    github_username: str
    display_name: str | None
    email: str | None
    streak: int
    longest_streak: int
    total_points: int
    spendable_points: int
    gas: int
    leetcode_username: str | None
    leetcode_validated: bool
    lifetime_stats: LifetimeStatsResponse
    personal_bests: list[PersonalBestResponse]
