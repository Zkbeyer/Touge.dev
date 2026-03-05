from datetime import date

from pydantic import BaseModel, computed_field


class TrackInfo(BaseModel):
    id: str
    name: str
    slug: str
    length_days: int
    difficulty: str


class RunState(BaseModel):
    id: str
    track: TrackInfo
    segment_index: int
    stopwatch_seconds: int
    corner_saves: int
    weather_penalties_taken: int
    ghost_wins: int
    start_date: date
    last_processed_date: date | None

    @computed_field
    @property
    def stopwatch_formatted(self) -> str:
        m, s = divmod(self.stopwatch_seconds, 60)
        return f"{m}:{s:02d}"

    @computed_field
    @property
    def progress_percent(self) -> int:
        if self.track.length_days == 0:
            return 0
        return min(100, int(self.segment_index / self.track.length_days * 100))


class UserSummary(BaseModel):
    id: str
    github_username: str
    streak: int
    longest_streak: int
    gas: int
    total_points: int
    spendable_points: int


class SummaryDayResponse(BaseModel):
    date: date
    qualified: bool
    gas_used: bool
    crashed: bool
    corner_completed: bool | None
    weather_survived: bool | None
    ghost_won: bool | None
    stopwatch_delta: int
    ghost_points: int = 0


class CatchUpSummaryResponse(BaseModel):
    days_processed: int
    net_streak_change: int
    gas_used: int
    crashed: bool
    stopwatch_delta: int
    ghost_wins: int
    run_completed: bool
    lootboxes_awarded: int
    days: list[SummaryDayResponse]


class RunResponse(BaseModel):
    run: RunState | None
    user: UserSummary
    catchup_summary: CatchUpSummaryResponse | None = None
