from datetime import date

from pydantic import BaseModel, computed_field


class SegmentInfo(BaseModel):
    type: str   # straight | sweeper | chicane | hairpin
    name: str


class TrackInfo(BaseModel):
    id: str
    name: str
    slug: str
    length_days: int
    difficulty: str
    segment_layout: list[SegmentInfo] | None = None


class RunState(BaseModel):
    id: str
    track: TrackInfo
    segment_index: int
    stopwatch_seconds: int
    corner_saves: int
    weather_penalties_taken: int
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

    @computed_field
    @property
    def current_segment(self) -> SegmentInfo | None:
        """The segment the car is currently on (1-based index into layout)."""
        layout = self.track.segment_layout
        if not layout or self.segment_index == 0:
            return None
        idx = self.segment_index - 1
        if 0 <= idx < len(layout):
            return layout[idx]
        return None


class UserSummary(BaseModel):
    id: str
    github_username: str
    streak: int
    longest_streak: int
    gas: int
    total_points: int
    spendable_points: int
    active_car_id: str | None = None


class SummaryDayResponse(BaseModel):
    date: date
    qualified: bool
    gas_used: bool
    crashed: bool
    corner_completed: bool | None
    weather_survived: bool | None
    stopwatch_delta: int


class CatchUpSummaryResponse(BaseModel):
    days_processed: int
    net_streak_change: int
    gas_used: int
    crashed: bool
    stopwatch_delta: int
    run_completed: bool
    days: list[SummaryDayResponse]


class TodayChallengeDetail(BaseModel):
    event_type: str
    corner_type: str | None = None
    weather_type: str | None = None
    requirement: dict | None = None
    current_value: int = 0
    met: bool = False
    time_save_seconds: int | None = None
    penalty_seconds: int | None = None


class TodayStatusResponse(BaseModel):
    qualified: bool
    streak_applied: bool
    segment_advanced: bool
    has_challenges: bool
    all_challenges_met: bool
    challenges: list[TodayChallengeDetail] = []


class RunResponse(BaseModel):
    run: RunState | None
    user: UserSummary
    catchup_summary: CatchUpSummaryResponse | None = None
    today_status: TodayStatusResponse | None = None
