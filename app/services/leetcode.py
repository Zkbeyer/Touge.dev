from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import httpx

from app.config import settings


class LeetCodeClient:
    def __init__(self):
        self.base_url = settings.lc_api_base_url.rstrip("/")

    async def validate_username(self, username: str) -> bool:
        """Returns True if the LeetCode username resolves to a valid profile."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/{username}")
                if resp.status_code != 200:
                    return False
                data = resp.json()
                # Valid profile has a username field
                return bool(data.get("username") or data.get("name") or data.get("totalSolved") is not None)
            except Exception:
                return False

    async def fetch_accepted_counts(
        self, username: str, target_date: date, user_tz: str = "UTC"
    ) -> dict[str, int]:
        """
        Returns counts of accepted submissions on target_date grouped by difficulty.
        {"easy": int, "medium": int, "hard": int, "total": int}
        """
        tz = ZoneInfo(user_tz)
        counts = {"easy": 0, "medium": 0, "hard": 0, "total": 0}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/{username}/submission",
                    params={"limit": 40},
                )
                if resp.status_code != 200:
                    return counts
                data = resp.json()
                submissions = data if isinstance(data, list) else data.get("submission", [])
            except Exception:
                return counts

        for sub in submissions:
            if sub.get("statusDisplay") != "Accepted":
                continue

            timestamp = sub.get("timestamp")
            if not timestamp:
                continue

            try:
                sub_dt = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).astimezone(tz)
            except (ValueError, TypeError):
                continue

            if sub_dt.date() != target_date:
                continue

            difficulty = (sub.get("difficulty") or "").lower()
            if difficulty == "easy":
                counts["easy"] += 1
            elif difficulty == "medium":
                counts["medium"] += 1
            elif difficulty == "hard":
                counts["hard"] += 1
            counts["total"] += 1

        return counts
