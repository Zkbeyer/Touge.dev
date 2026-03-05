from datetime import date, datetime, timedelta, timezone

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.activity import DailyActivity
from app.models.oauth import OAuthToken
from app.models.user import User
from app.services.github import GitHubClient, GitHubRateLimitError
from app.services.leetcode import LeetCodeClient

FINALIZE_AFTER_HOURS = 48


def _get_fernet() -> Fernet:
    return Fernet(settings.token_encryption_key.encode() if isinstance(settings.token_encryption_key, str) else settings.token_encryption_key)


async def _decrypt_token(user_id, db: AsyncSession) -> str | None:
    token_row = await db.scalar(select(OAuthToken).where(OAuthToken.user_id == user_id))
    if not token_row:
        return None
    fernet = _get_fernet()
    return fernet.decrypt(token_row.access_token_enc).decode()


async def get_or_fetch_activity(
    user: User, target_date: date, db: AsyncSession, force_refetch: bool = False
) -> DailyActivity:
    """
    Returns DailyActivity for user on target_date.
    Fetches from providers if missing or not finalized.
    """
    now_utc = datetime.now(timezone.utc)
    existing = await db.scalar(
        select(DailyActivity).where(
            DailyActivity.user_id == user.id,
            DailyActivity.date == target_date,
        )
    )

    # Already finalized — never refetch
    if existing and existing.is_finalized and not force_refetch:
        return existing

    # Don't refetch if fetched recently (< 6 hours ago) unless finalized check needed
    if existing and existing.fetched_at and not force_refetch:
        age = now_utc - existing.fetched_at.replace(tzinfo=timezone.utc)
        if age.total_seconds() < 6 * 3600:
            return existing

    # Fetch from GitHub
    github_count = 0
    access_token = await _decrypt_token(user.id, db)
    if access_token:
        try:
            gh_client = GitHubClient(access_token)
            github_count = await gh_client.fetch_commit_count(
                user.github_username, target_date, user.timezone
            )
        except GitHubRateLimitError:
            # Use existing data if available
            github_count = existing.github_commit_count if existing else 0
        except Exception:
            github_count = existing.github_commit_count if existing else 0

    # Fetch from LeetCode (if configured)
    lc_easy = lc_medium = lc_hard = lc_total = 0
    if user.leetcode_validated and user.leetcode_username:
        try:
            lc_client = LeetCodeClient()
            lc_counts = await lc_client.fetch_accepted_counts(
                user.leetcode_username, target_date, user.timezone
            )
            lc_easy = lc_counts["easy"]
            lc_medium = lc_counts["medium"]
            lc_hard = lc_counts["hard"]
            lc_total = lc_counts["total"]
        except Exception:
            if existing:
                lc_easy = existing.lc_easy_accepted
                lc_medium = existing.lc_medium_accepted
                lc_hard = existing.lc_hard_accepted
                lc_total = existing.lc_total_accepted

    # Determine if we should finalize
    date_age_hours = (now_utc.date() - target_date).days * 24
    should_finalize = date_age_hours >= FINALIZE_AFTER_HOURS

    # Upsert
    stmt = insert(DailyActivity).values(
        user_id=user.id,
        date=target_date,
        github_commit_count=github_count,
        lc_easy_accepted=lc_easy,
        lc_medium_accepted=lc_medium,
        lc_hard_accepted=lc_hard,
        lc_total_accepted=lc_total,
        fetched_at=now_utc,
        is_finalized=should_finalize,
    ).on_conflict_do_update(
        constraint="uq_daily_activity_user_date",
        set_={
            "github_commit_count": github_count,
            "lc_easy_accepted": lc_easy,
            "lc_medium_accepted": lc_medium,
            "lc_hard_accepted": lc_hard,
            "lc_total_accepted": lc_total,
            "fetched_at": now_utc,
            "is_finalized": should_finalize,
        },
    ).returning(DailyActivity)

    result = await db.execute(stmt)
    activity = result.scalar_one()
    return activity
