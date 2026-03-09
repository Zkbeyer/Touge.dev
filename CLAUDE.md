# Mountain Pass Streak — Project Reference

## Stack
- FastAPI + SQLAlchemy 2 (async) + PostgreSQL + Redis + Celery
- Python 3.12, uv for package management
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS v3 + React Three Fiber + Framer Motion + TanStack Query v5 + Zustand

## Key Architectural Decisions
- GitHub OAuth is REQUIRED. LeetCode is OPTIONAL (validated username).
- All event outcomes (corner/weather/ghost) are deterministically rolled via SHA-256(user_id:date:event_type:v1) and stored in daily_run_events on first encounter. Never re-rolled.
- process_user_days() is idempotent: protected by pg_advisory_xact_lock + UNIQUE constraints.
- "Qualified day" = github_commit_count > 0 OR (lc_validated AND lc_total_accepted > 0)
- Gas covers missed days (streak preserved). No gas = crash (streak=0, run resets to segment 0, stopwatch=0).
- Stopwatch: base_time + weather_penalties - corner_saves. Never goes below 0. Ghost wins don't affect stopwatch.
- Lootboxes contain CARS ONLY. Cosmetics (drift/music/sounds) come from ghost/rival wins only.
- Upgrades cost spendable_points (separate from total_points). Max upgrade -> Iconic look + perk.

## Critical Files
- app/services/processor.py — core game loop
- app/services/events.py — deterministic rolling
- app/services/lootbox.py — rewards
- seeds/ — track/car/perk/cosmetic catalog
- alembic/versions/ — migrations
- app/main.py — serves frontend/dist/ as static files (SPA fallback)
- frontend/src/App.tsx — auth gate + view router + QueryClientProvider
- frontend/src/store/index.ts — Zustand store (token persisted)
- frontend/src/lib/api.ts — typed fetch client (Bearer token, auto-logout on 401)
- frontend/src/scene/MountainScene.tsx — R3F canvas entry

## Frontend Dev
- `cd frontend && npm run dev` → Vite dev server :5173, proxies all API paths to :8000
- `npm run build` → outputs to frontend/dist/ (served by FastAPI)
- Design: warm paper tones (#f5f3ef) for UI chrome; dark scene-bg (#0d0c12) inside R3F canvas only
- Settings endpoint: PUT /settings/leetcode {username}, DELETE /settings/leetcode (not POST)

## Conventions
- All timestamps in UTC in DB; convert to user TZ at read time.
- UUIDs for all PKs.
- Fernet-encrypt OAuth tokens; key in TOKEN_ENCRYPTION_KEY env var.
- Never re-fetch is_finalized=True daily_activity rows.
- is_finalized set to True for dates older than 48h.

## Perk Slugs
smooth_line, draft_master, rain_tires, lucky_find, hairpin_specialist, momentum, fuel_economy

## Event Thresholds
- Corner: roll < 0.60
- Weather: roll < 0.40
- Ghost: roll < 0.30

## Lootbox Tiers
- platinum >= 120 pts, gold >= 80, silver >= 50, bronze >= 0

## Gas
- Base drop chance: 15% on run completion
- lucky_find perk: +10% -> 25%
