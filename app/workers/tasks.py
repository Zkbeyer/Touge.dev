import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.workers.celery_app import app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


@app.task(name="app.workers.tasks.sync_all_active_users")
def sync_all_active_users():
    """
    Runs every hour via celery-beat.
    For each user active in last 30 days, triggers catch-up processing.
    """
    async def _run():
        from app.database import SessionLocal
        from app.models.activity import DailyActivity
        from app.models.user import User

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        async with SessionLocal() as db:
            # Find users with recent activity
            user_ids = (await db.scalars(
                select(DailyActivity.user_id)
                .where(DailyActivity.fetched_at >= cutoff)
                .distinct()
            )).all()

            # Also include users with active runs (may not have fetched activity yet)
            from app.models.run import Run
            run_user_ids = (await db.scalars(
                select(Run.user_id).where(Run.is_complete == False)
            )).all()

            all_user_ids = set(map(str, user_ids)) | set(map(str, run_user_ids))

        for user_id in all_user_ids:
            process_user_catchup.delay(user_id)

        logger.info(f"Queued catch-up for {len(all_user_ids)} users")

    _run_async(_run())


@app.task(
    name="app.workers.tasks.process_user_catchup",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def process_user_catchup(self, user_id: str):
    """
    Process catch-up for a single user.
    Called on login and by sync_all_active_users.
    """
    import uuid as uuid_lib

    async def _run():
        from datetime import timedelta
        from app.database import SessionLocal
        from app.models.run import Run
        from app.models.user import User
        from app.services.processor import process_user_days

        uid = uuid_lib.UUID(user_id)

        async with SessionLocal() as db:
            user = await db.get(User, uid)
            if not user:
                logger.warning(f"User {user_id} not found for catch-up")
                return

            tz = ZoneInfo(user.timezone)
            today = datetime.now(tz).date()
            yesterday = today - timedelta(days=1)

            run = await db.scalar(
                select(Run).where(Run.user_id == uid, Run.is_complete == False)
            )

            if run and run.last_processed_date:
                from_date = run.last_processed_date + timedelta(days=1)
            elif run:
                from_date = run.start_date
            else:
                from_date = today

            to_date = yesterday

            if from_date > to_date:
                return

            await process_user_days(uid, from_date, to_date, db)
            logger.info(f"Processed catch-up for user {user_id} from {from_date} to {to_date}")

    try:
        _run_async(_run())
    except Exception as exc:
        logger.error(f"Catch-up failed for user {user_id}: {exc}")
        raise self.retry(exc=exc)


@app.task(name="app.workers.tasks.fetch_github_activity")
def fetch_github_activity(user_id: str, target_date: str):
    """Fetch GitHub activity for a user on a specific date."""
    import uuid as uuid_lib
    from datetime import date

    async def _run():
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.activity import get_or_fetch_activity

        uid = uuid_lib.UUID(user_id)
        td = date.fromisoformat(target_date)

        async with SessionLocal() as db:
            user = await db.get(User, uid)
            if not user:
                return
            await get_or_fetch_activity(user, td, db, force_refetch=False)

    _run_async(_run())


@app.task(name="app.workers.tasks.fetch_leetcode_activity")
def fetch_leetcode_activity(user_id: str, target_date: str):
    """Fetch LeetCode activity for a user on a specific date."""
    import uuid as uuid_lib
    from datetime import date

    async def _run():
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.activity import get_or_fetch_activity

        uid = uuid_lib.UUID(user_id)
        td = date.fromisoformat(target_date)

        async with SessionLocal() as db:
            user = await db.get(User, uid)
            if not user or not user.leetcode_validated:
                return
            await get_or_fetch_activity(user, td, db, force_refetch=False)

    _run_async(_run())
