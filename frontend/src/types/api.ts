// ─── Auth ────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: string
  github_username: string
  display_name: string | null
  email: string | null
  timezone: string
  streak: number
  longest_streak: number
  total_points: number
  spendable_points: number
  gas: number
  leetcode_validated: boolean
  leetcode_username: string | null
  active_car_id: string | null
}

// ─── Run ─────────────────────────────────────────────────────────────────────

export interface SegmentInfo {
  type: 'straight' | 'sweeper' | 'chicane' | 'hairpin'
  name: string
}

export interface TrackInfo {
  id: string
  name: string
  slug: string
  length_days: number
  difficulty: string
  segment_layout: SegmentInfo[] | null
}

export interface RunState {
  id: string
  track: TrackInfo
  segment_index: number
  stopwatch_seconds: number
  corner_saves: number
  weather_penalties_taken: number
  start_date: string
  last_processed_date: string | null
  stopwatch_formatted: string
  progress_percent: number
  current_segment: SegmentInfo | null
}

export interface UserSummary {
  id: string
  github_username: string
  streak: number
  longest_streak: number
  gas: number
  total_points: number
  spendable_points: number
  active_car_id: string | null
}

export interface TodayChallengeDetail {
  event_type: string
  corner_type: string | null
  weather_type: string | null
  requirement: Record<string, unknown> | null
  current_value: number | null
  required_value: number
  met: boolean
  time_save_seconds: number | null
  penalty_seconds: number | null
}

export interface TodayStatusResponse {
  qualified: boolean
  streak_applied: boolean
  segment_advanced: boolean
  has_challenges: boolean
  all_challenges_met: boolean
  challenges: TodayChallengeDetail[]
}

export interface SummaryDayResponse {
  date: string
  qualified: boolean
  gas_used: boolean
  crashed: boolean
  corner_completed: boolean | null
  weather_survived: boolean | null
  stopwatch_delta: number
}

export interface CatchUpSummaryResponse {
  days_processed: number
  net_streak_change: number
  gas_used: number
  crashed: boolean
  stopwatch_delta: number
  run_completed: boolean
  days: SummaryDayResponse[]
}

export interface RunResponse {
  run: RunState | null
  user: UserSummary
  catchup_summary: CatchUpSummaryResponse | null
  today_status: TodayStatusResponse
}

// ─── Garage (disabled — re-enable later) ─────────────────────────────────────

export interface PerkInfo {
  id: string
  slug: string
  name: string
  description: string
  effect_type: string
  effect_value: number
}

export interface CarCatalogInfo {
  id: string
  name: string
  slug: string
  rarity: string
  description: string
  base_model: string
  max_upgrade_level: number
  perk: PerkInfo | null
}

export interface OwnedCar {
  id: string
  car: CarCatalogInfo
  upgrade_level: number
  iconic_unlocked: boolean
  perk_active: boolean
  obtained_at: string
}

export interface UpgradeResponse {
  new_level: number
  iconic_unlocked: boolean
  perk_unlocked: boolean
  cost_paid: number
  remaining_spendable: number
}

export interface Cosmetic {
  id: string
  slug: string
  name: string
  type: string
  rarity: string
  source_description: string
  obtained_at: string
}

// ─── Inventory (disabled — re-enable later) ───────────────────────────────────

export interface Lootbox {
  id: string
  tier: string
  created_at: string
}

export interface OpenLootboxResult {
  type: string
  rarity: string
  car_id: string | null
  car_name: string | null
  points: number | null
}

// ─── Profile ─────────────────────────────────────────────────────────────────

export interface LifetimeStats {
  total_runs_completed: number
  total_days_qualified: number
  total_gas_used: number
  total_crashes: number
  total_corner_saves: number
  total_weather_survived: number
  total_lootboxes_opened: number
  total_cars_owned: number
}

export interface PersonalBest {
  track_id: string
  track_name: string
  track_slug: string
  best_seconds: number
  best_formatted: string
  set_at: string
}

export interface ProfileResponse {
  id: string
  github_username: string
  display_name: string | null
  email: string | null
  streak: number
  longest_streak: number
  total_points: number
  spendable_points: number
  gas: number
  leetcode_username: string | null
  leetcode_validated: boolean
  lifetime_stats: LifetimeStats
  personal_bests: PersonalBest[]
}

// ─── Settings ────────────────────────────────────────────────────────────────

export interface SettingsResponse {
  leetcode_username: string | null
  leetcode_validated: boolean
}
