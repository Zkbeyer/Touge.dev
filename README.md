# Mountain Pass Streak

A single-player gamified coding streak app with a retro touge/Initial D aesthetic. Every day you code, your car advances down a mountain pass. Skip a day and you crash.

- [Setup](#setup)
- [Running Tests](#running-tests)
- [API Reference](#api-reference)
- [Game Rules](#game-rules)
- [Architecture](#architecture)

---

## Setup

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- uv (`pip install uv`)
- A GitHub OAuth App ([create one here](https://github.com/settings/developers))

### 1. Install dependencies

```bash
uv pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — the required values are:

| Variable | How to get it |
|---|---|
| `GITHUB_CLIENT_ID` | GitHub OAuth App → Client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth App → Client Secret |
| `GITHUB_REDIRECT_URI` | Must match your OAuth App's callback URL (e.g. `http://localhost:8000/auth/github/callback`) |
| `TOKEN_ENCRYPTION_KEY` | Run: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `SECRET_KEY` | Any random string ≥32 chars |

### 3. Start backing services

```bash
docker compose up -d postgres redis
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Seed catalog data

Seeds tracks, cars, perks, and cosmetics into the database.

```bash
python seeds/seed.py
```

### 6. Start the server

```bash
uvicorn app.main:app --reload
```

API is now at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Full stack with Docker

Starts the API, Celery worker, Celery beat scheduler, Postgres, and Redis together:

```bash
docker compose up
```

---

## Running Tests

### Unit + integration tests

Tests use an in-memory SQLite database — no Postgres or Redis needed.

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_processor.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### What's tested

| File | What it covers |
|---|---|
| `tests/test_events.py` | SHA-256 roll determinism, range [0,1), event probability thresholds, idempotency of `get_or_roll_events` |
| `tests/test_lootbox.py` | Tier scoring thresholds, drop rate sums to 1.0, open logic, duplicate → points conversion |
| `tests/test_processor.py` | Qualified day → segment advances, gas consumption on miss, crash on no-gas, idempotency, multi-day catch-up, run completion |

### Manual API testing

With the server running:

```bash
# Health check
curl http://localhost:8000/health

# Start OAuth flow (opens browser)
open http://localhost:8000/auth/github

# After OAuth completes and you have a JWT:
TOKEN="your_jwt_here"

# Get current run state
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/run

# Manually process today
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/run/process

# View profile
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/profile
```

---

## API Reference

All authenticated endpoints require `Authorization: Bearer <jwt>` header. The JWT is returned by the OAuth callback.

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/auth/github` | No | Redirect to GitHub OAuth consent |
| `GET` | `/auth/github/callback` | No | OAuth callback — returns `{"access_token": "...", "token_type": "bearer"}` |
| `GET` | `/auth/me` | Yes | Current user info |
| `POST` | `/auth/logout` | Yes | Logout (client should discard JWT) |

### Settings

| Method | Path | Body | Description |
|---|---|---|---|
| `PUT` | `/settings/leetcode` | `{"username": "lc_user"}` | Validate and save LeetCode username |
| `DELETE` | `/settings/leetcode` | — | Remove LeetCode integration |

### Run

| Method | Path | Description |
|---|---|---|
| `GET` | `/run` | Current run state. Auto-triggers catch-up for any unprocessed days up to yesterday. |
| `POST` | `/run/process` | Manually trigger catch-up including today. |

**`GET /run` response example:**
```json
{
  "run": {
    "id": "...",
    "track": { "name": "Akina Downhill", "length_days": 14, "difficulty": "beginner" },
    "segment_index": 5,
    "stopwatch_seconds": 243,
    "stopwatch_formatted": "4:03",
    "progress_percent": 35,
    "corner_saves": 2,
    "weather_penalties_taken": 1,
    "ghost_wins": 1
  },
  "user": { "streak": 5, "gas": 1, "spendable_points": 350 },
  "catchup_summary": {
    "days_processed": 3,
    "net_streak_change": 2,
    "gas_used": 1,
    "crashed": false,
    "stopwatch_delta": 142,
    "ghost_wins": 1,
    "run_completed": false,
    "lootboxes_awarded": 0,
    "days": [
      {
        "date": "2026-03-03",
        "qualified": true,
        "gas_used": false,
        "crashed": false,
        "corner_completed": true,
        "weather_survived": true,
        "ghost_won": false,
        "stopwatch_delta": 38,
        "ghost_points": 0
      }
    ]
  }
}
```

`catchup_summary` is `null` if already up to date.

### Inventory

| Method | Path | Description |
|---|---|---|
| `GET` | `/inventory/lootboxes` | List all unopened lootboxes |
| `POST` | `/inventory/lootboxes/{id}/open` | Open a lootbox. Returns car or points if duplicate. |

**Open lootbox response:**
```json
{ "type": "car", "rarity": "rare", "car_id": "...", "car_name": "The Widow Maker" }
// or
{ "type": "duplicate_points", "rarity": "rare", "car_name": "The Widow Maker", "points": 150 }
```

### Garage

| Method | Path | Body | Description |
|---|---|---|---|
| `GET` | `/garage/cars` | — | All owned cars with upgrade level, perk, iconic status |
| `POST` | `/garage/cars/{ownership_id}/select` | — | Set as active car |
| `POST` | `/garage/cars/{ownership_id}/upgrade` | — | Upgrade one level (costs spendable_points) |
| `POST` | `/garage/cars/{ownership_id}/perk` | `{"active": true}` | Toggle perk on/off (requires max upgrade level) |
| `GET` | `/garage/cosmetics` | — | All owned drift effects, music tracks, engine sounds |

**Upgrade costs by rarity (per level):**

| Level | Common | Rare | Epic | Legendary |
|---|---|---|---|---|
| 0→1 | 100 | 150 | 250 | 400 |
| 1→2 | 200 | 300 | 500 | 800 |
| 2→3 | 350 | 525 | 875 | 1400 |
| 3→4 | 500 | 750 | 1250 | 2000 |
| 4→5 (Iconic) | 750 | 1125 | 1875 | 3000 |

### Profile

| Method | Path | Description |
|---|---|---|
| `GET` | `/profile` | Lifetime stats + all personal bests |
| `GET` | `/profile/pbs` | Personal best times by track |

---

## Game Rules

### Qualified Day
A day qualifies if:
- `github_commit_count > 0` (any push event on your GitHub account), **OR**
- `leetcode_validated = true` AND `lc_total_accepted > 0`

LeetCode is optional. If you haven't set a LeetCode username, only commits count.

### Streak & Crash
- Each qualified day: `streak += 1`, `segment_index += 1`
- Miss a day with **gas**: gas consumed, segment still advances, streak preserved
- Miss a day with **no gas**: **CRASH** — `streak = 0`, `segment_index = 0`, `stopwatch = 0`

### Stopwatch
Each segment: `stopwatch += base_time + weather_penalties - corner_saves`. Never goes below 0.

Ghost wins give points and cosmetics but do **not** affect the stopwatch.

### Events (per day, rolled once and stored)
| Event | Chance | Effect |
|---|---|---|
| Corner | 60% | Complete the activity requirement → save 10–30 seconds |
| Weather | 40% | Fail the requirement → add 15–45 second penalty |
| Ghost | 30% | Win → earn 50–200 points + 10% cosmetic drop chance |

Event outcomes are deterministic: `SHA-256(user_id:date:event_type:v1)`. Same day always has the same events.

### Run Completion
When `segment_index >= track.length_days`:
- Run is archived
- Performance score calculated → lootbox tier awarded (bronze/silver/gold/platinum)
- 15% chance of 1 gas drop (25% with `lucky_find` perk active)
- New run starts on a different track
- Personal best checked and updated

### Lootbox Tiers
| Score | Tier | Legendary chance |
|---|---|---|
| 0–49 | Bronze | 0.2% |
| 50–79 | Silver | 1% |
| 80–119 | Gold | 5% |
| 120+ | Platinum | 15% |

Lootboxes contain **cars only**. Duplicate car = converted to points.

### Perks
Perks unlock when a car reaches max upgrade level (level 5). Toggle on/off anytime.

| Perk | Car Rarity | Effect |
|---|---|---|
| Smooth Line | Common | Base segment time −5% |
| Rain Tires | Common/Rare | Weather penalties −15% |
| Hairpin Specialist | Common/Epic | Corner saves +8% |
| Draft Master | Rare/Legendary | Ghost win points +10% |
| Lucky Find | Rare | Gas drop chance +10% |
| Momentum | Epic/Legendary | At 10+ streak: absorb 1 crash (once per run) |
| Fuel Economy | Epic | Gas covers 2 consecutive missed days |

---

## Architecture

See `CLAUDE.md` for full architectural decisions and conventions.

### Key design principles

- **Deterministic events**: All per-day events (corner/weather/ghost) are rolled via `SHA-256(user_id:date:event_type:v1)` on first encounter and stored. Retries never change outcomes.
- **Idempotent processing**: `process_user_days()` uses `pg_advisory_xact_lock` + `UNIQUE(user_id, date)` constraints. Safe to call multiple times.
- **Finalization**: Activity older than 48h is marked `is_finalized=True` and never re-fetched from providers.
- **Token security**: GitHub OAuth tokens are Fernet-encrypted at rest. Key lives in `TOKEN_ENCRYPTION_KEY` env var.

### Folder structure

```
app/
  models/       — SQLAlchemy ORM models
  schemas/      — Pydantic request/response schemas
  routers/      — FastAPI route handlers
  services/     — Business logic (processor, events, lootbox, garage, github, leetcode)
  workers/      — Celery tasks + beat schedule
seeds/          — JSON catalog data + seed script
alembic/        — Database migrations
tests/          — pytest test suite
```
